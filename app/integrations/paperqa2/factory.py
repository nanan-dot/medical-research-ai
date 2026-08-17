"""Lazy fixed-version PaperQA2 backend and application factory."""

from __future__ import annotations

import asyncio
import importlib.metadata
import ipaddress
import threading
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import SecretStr

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
        rebuild: bool = False,
    ) -> _BackendIndexResult:
        self._check_installed_version()
        with self._lock:
            if index_id in self._indexes and not rebuild:
                return _BackendIndexResult(index_id, len(documents), True)
            try:
                docs = asyncio.run(self._build_docs(documents))
            except Exception as error:
                raise PaperQA2OperationError(
                    "PaperQA2 could not index the documents"
                ) from error
            self._indexes[index_id] = docs
            return _BackendIndexResult(index_id, len(documents), False)

    def ask(self, index_id: str, question: str) -> Any:
        self._check_installed_version()
        with self._lock:
            docs = self._indexes.get(index_id)
            if docs is None:
                raise PaperQA2IndexNotFoundError(
                    "PaperQA2 index is unavailable in this process"
                )
            if not hasattr(docs, "aquery") or not hasattr(docs, "docs"):
                raise PaperQA2IndexCorruptError(
                    "PaperQA2 index is incompatible or corrupted"
                )
            try:
                return asyncio.run(
                    docs.aquery(question, settings=self._make_settings())
                )
            except Exception as error:
                raise PaperQA2OperationError(
                    "PaperQA2 could not answer the question"
                ) from error

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
                        "model": f"{self.config.provider}/{self.config.llm_model}",
                        "api_base": self.config.api_base_url,
                        **(
                            {"api_key": self.config.api_key.get_secret_value()}
                            if self.config.api_key
                            else {}
                        ),
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
                "api_base": self.config.api_base_url,
                "timeout": self.config.timeout_seconds,
            },
        )
        paperqa_settings.parsing.use_doc_details = False
        # 文档已通过本项目解析器校验；允许 PaperQA 使用其 Office 读取器。
        paperqa_settings.parsing.disable_doc_valid_check = True
        paperqa_settings.parsing.reader_config = {"chunk_chars": 1600, "overlap": 120}
        multimodal_options: Any = type(paperqa_settings.parsing.multimodal)
        paperqa_settings.parsing.multimodal = multimodal_options.OFF
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


def create_paperqa2_client(
    app_settings: AppSettings = settings,
    *,
    provider: Literal["ollama", "openai", "openrouter"] | None = None,
) -> PaperQA2Client:
    selected_provider = provider or app_settings.DEFAULT_MODEL_PROVIDER
    model, base_url, api_key = {
        "ollama": (app_settings.OLLAMA_MODEL, app_settings.OLLAMA_BASE_URL, None),
        "openai": (
            app_settings.OPENAI_MODEL,
            app_settings.OPENAI_BASE_URL,
            app_settings.OPENAI_API_KEY,
        ),
        "openrouter": (
            app_settings.OPENROUTER_MODEL,
            app_settings.OPENROUTER_BASE_URL,
            app_settings.OPENROUTER_API_KEY,
        ),
    }[selected_provider]
    if selected_provider == "ollama":
        _validate_local_ollama_url(base_url)
    elif not api_key:
        raise PaperQA2ConfigurationError(
            f"{selected_provider.upper()} API key is not configured"
        )
    if not model:
        raise PaperQA2ConfigurationError(
            f"{selected_provider.upper()}_MODEL is not configured"
        )
    config = PaperQA2Config(
        version=app_settings.PAPERQA_VERSION,
        provider=selected_provider,
        api_base_url=base_url.rstrip("/"),
        api_key=SecretStr(api_key) if api_key else None,
        llm_model=model,
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
        raise PaperQA2ConfigurationError(
            "PaperQA2 Ollama URL must use a loopback address"
        )
