"""Lazy fixed-version PaperQA2 backend and application factory."""

from __future__ import annotations

import asyncio
import importlib.metadata
import ipaddress
import threading
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings as AppSettings
from app.core.config import settings
from app.integrations.paperqa2.client import PaperQA2Client, _BackendIndexResult
from app.integrations.paperqa2.exceptions import (
    PaperQA2ConfigurationError,
    PaperQA2IndexCorruptError,
    PaperQA2IndexNotFoundError,
    PaperQA2NotInstalledError,
    PaperQA2OperationError,
    PaperQA2VersionError,
)
from app.integrations.paperqa2.schemas import PaperDocument, PaperQA2Config


class _OfficialPaperQA2Backend:
    """Own all external PaperQA2 types inside this private backend."""

    def __init__(self, config: PaperQA2Config):
        self.config = config
        self._indexes: dict[str, Any] = {}
        self._lock = threading.Lock()

    def index_documents(
        self,
        documents: tuple[PaperDocument, ...],
        index_id: str,
    ) -> _BackendIndexResult:
        self._check_installed_version()
        with self._lock:
            if index_id in self._indexes:
                return _BackendIndexResult(index_id, len(documents), True)
            try:
                docs = asyncio.run(self._build_docs(documents))
            except Exception as error:
                raise PaperQA2OperationError("PaperQA2 could not index the documents") from error
            self._indexes[index_id] = docs
            return _BackendIndexResult(index_id, len(documents), False)

    def ask(self, index_id: str, question: str) -> Any:
        self._check_installed_version()
        with self._lock:
            docs = self._indexes.get(index_id)
            if docs is None:
                raise PaperQA2IndexNotFoundError("PaperQA2 index is unavailable in this process")
            if not hasattr(docs, "aquery") or not hasattr(docs, "docs"):
                raise PaperQA2IndexCorruptError("PaperQA2 index is incompatible or corrupted")
            try:
                return asyncio.run(docs.aquery(question, settings=self._make_settings()))
            except Exception as error:
                raise PaperQA2OperationError("PaperQA2 could not answer the question") from error

    async def _build_docs(self, documents: tuple[PaperDocument, ...]) -> Any:
        from paperqa import Docs

        docs = Docs()
        paperqa_settings = self._make_settings()
        for document in documents:
            await docs.aadd(
                document.path,
                citation=document.citation or document.path.name,
                title=document.title,
                docname=document.path.stem,
                settings=paperqa_settings,
            )
        return docs

    def _make_settings(self) -> Any:
        from paperqa import Settings

        router = {
            "model_list": [
                {
                    "model_name": "local-paperqa-r0",
                    "litellm_params": {
                        "model": f"ollama/{self.config.llm_model}",
                        "api_base": self.config.ollama_base_url,
                        "timeout": self.config.timeout_seconds,
                        "num_ctx": 16384,
                        "max_tokens": 2000,
                        "think": False,
                    },
                }
            ]
        }
        paperqa_settings = Settings(
            llm="local-paperqa-r0",
            llm_config=router,
            summary_llm="local-paperqa-r0",
            summary_llm_config=router,
            embedding=f"ollama/{self.config.embedding_model}",
            embedding_config={
                "api_base": self.config.ollama_base_url,
                "timeout": self.config.timeout_seconds,
            },
        )
        paperqa_settings.parsing.use_doc_details = False
        paperqa_settings.parsing.reader_config = {"chunk_chars": 1600, "overlap": 120}
        paperqa_settings.parsing.multimodal = type(paperqa_settings.parsing.multimodal).OFF
        paperqa_settings.answer.evidence_skip_summary = True
        paperqa_settings.answer.evidence_k = 10
        paperqa_settings.answer.answer_max_sources = 5
        return paperqa_settings

    def _check_installed_version(self) -> None:
        try:
            installed = importlib.metadata.version("paper-qa")
        except importlib.metadata.PackageNotFoundError as error:
            raise PaperQA2NotInstalledError(
                f"paper-qa=={self.config.version} is required in the adapter runtime"
            ) from error
        if installed != self.config.version:
            raise PaperQA2VersionError(
                f"paper-qa=={self.config.version} is required; found {installed}"
            )


def create_paperqa2_client(app_settings: AppSettings = settings) -> PaperQA2Client:
    _validate_local_ollama_url(app_settings.OLLAMA_BASE_URL)
    if not app_settings.OLLAMA_MODEL:
        raise PaperQA2ConfigurationError("OLLAMA_MODEL is not configured")
    config = PaperQA2Config(
        version=app_settings.PAPERQA_VERSION,
        ollama_base_url=app_settings.OLLAMA_BASE_URL.rstrip("/"),
        llm_model=app_settings.OLLAMA_MODEL,
        embedding_model=app_settings.PAPERQA_EMBEDDING_MODEL,
        timeout_seconds=app_settings.PAPERQA_TIMEOUT_SECONDS,
    )
    return PaperQA2Client(config, _OfficialPaperQA2Backend(config))


def _validate_local_ollama_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "http" or not parsed.hostname:
        raise PaperQA2ConfigurationError("PaperQA2 Ollama URL must be a local HTTP URL")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        is_loopback = parsed.hostname == "localhost"
    if not is_loopback:
        raise PaperQA2ConfigurationError("PaperQA2 Ollama URL must use a loopback address")
