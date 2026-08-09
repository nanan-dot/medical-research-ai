"""Async adapter that keeps PaperQA2 objects behind an application-owned boundary."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.integrations.paperqa2.exceptions import (
    PaperQA2DocumentError,
    PaperQA2Error,
    PaperQA2OperationError,
    PaperQA2ResponseError,
)
from app.integrations.paperqa2.schemas import (
    PaperDocument,
    PaperQA2Config,
    PaperQAAnswer,
    PaperQAIndex,
    PaperSource,
)

MAX_SOURCE_EXCERPT_CHARS = 1000


@dataclass(frozen=True)
class _BackendIndexResult:
    index_id: str
    document_count: int
    reused: bool


class _PaperQA2Backend(Protocol):
    def index_documents(
        self,
        documents: tuple[PaperDocument, ...],
        index_id: str,
        rebuild: bool = False,
    ) -> _BackendIndexResult: ...

    def ask(self, index_id: str, question: str) -> Any: ...


class PaperQA2Client:
    """Expose only project schemas while running blocking integration work in threads."""

    def __init__(self, config: PaperQA2Config, backend: _PaperQA2Backend):
        self.config = config
        self._backend = backend

    async def index_documents(
        self,
        documents: Sequence[PaperDocument | str | Path],
        *,
        rebuild: bool = False,
    ) -> PaperQAIndex:
        try:
            normalized, index_id = await asyncio.to_thread(
                self._normalize_documents, documents
            )
            result = await asyncio.to_thread(
                self._backend.index_documents,
                normalized,
                index_id,
                rebuild,
            )
        except PaperQA2Error:
            raise
        except Exception as error:
            raise PaperQA2OperationError("PaperQA2 document indexing failed") from error

        return PaperQAIndex(
            index_id=result.index_id,
            document_count=result.document_count,
            reused=result.reused,
        )

    async def ask(self, index: PaperQAIndex | str, question: str) -> PaperQAAnswer:
        index_id = index.index_id if isinstance(index, PaperQAIndex) else index
        if not index_id.strip():
            raise PaperQA2DocumentError(
                "A non-empty PaperQA2 index identifier is required"
            )
        if not question.strip():
            raise PaperQA2DocumentError("A non-empty PaperQA2 question is required")

        try:
            session = await asyncio.to_thread(
                self._backend.ask, index_id, question.strip()
            )
            return self._convert_answer(session, index_id)
        except PaperQA2Error:
            raise
        except Exception as error:
            raise PaperQA2OperationError(
                "PaperQA2 question answering failed"
            ) from error

    @staticmethod
    def _normalize_documents(
        documents: Sequence[PaperDocument | str | Path],
    ) -> tuple[tuple[PaperDocument, ...], str]:
        if not documents:
            raise PaperQA2DocumentError("At least one document is required")

        normalized: list[PaperDocument] = []
        fingerprints: list[str] = []
        for value in documents:
            document = (
                value
                if isinstance(value, PaperDocument)
                else PaperDocument(path=Path(value))
            )
            path = document.path.resolve()
            if not path.is_file():
                raise PaperQA2DocumentError(f"Document does not exist: {path.name}")
            digest = PaperQA2Client._sha256_file(path)
            normalized.append(document.model_copy(update={"path": path}))
            fingerprints.append(f"{path.as_posix()}\0{digest}")

        pairs = sorted(
            zip(fingerprints, normalized, strict=True), key=lambda item: item[0]
        )
        ordered = tuple(document for _, document in pairs)
        index_digest = hashlib.sha256(
            "\n".join(sorted(fingerprints)).encode()
        ).hexdigest()
        return ordered, f"pqa2-{index_digest[:24]}"

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @classmethod
    def _convert_answer(cls, session: Any, index_id: str) -> PaperQAAnswer:
        answer = getattr(session, "answer", None) or getattr(
            session, "raw_answer", None
        )
        if not isinstance(answer, str) or not answer.strip():
            raise PaperQA2ResponseError("PaperQA2 returned an empty answer")

        contexts = getattr(session, "contexts", [])
        if contexts is None:
            contexts = []
        if not isinstance(contexts, (list, tuple)):
            raise PaperQA2ResponseError("PaperQA2 returned incompatible source data")

        return PaperQAAnswer(
            answer=answer.strip(),
            index_id=index_id,
            sources=[cls._convert_source(context) for context in contexts],
        )

    @staticmethod
    def _convert_source(context: Any) -> PaperSource:
        text = getattr(context, "text", None)
        document = getattr(text, "doc", None)
        chunk_name = getattr(text, "name", None)
        if chunk_name is not None and not isinstance(chunk_name, str):
            chunk_name = None
        page_match = re.search(r"\bpages?\s+(\d+)(?:-(\d+))?", chunk_name or "", re.IGNORECASE)

        title = getattr(document, "title", None) or getattr(document, "docname", None)
        citation = getattr(document, "citation", None)
        excerpt = getattr(context, "context", None) or getattr(text, "text", None)
        score = getattr(context, "score", None)
        return PaperSource(
            source_id=chunk_name,
            title=title if isinstance(title, str) and title.strip() else None,
            citation=citation
            if isinstance(citation, str) and citation.strip()
            else None,
            page_start=int(page_match.group(1)) if page_match else None,
            page_end=int(page_match.group(2) or page_match.group(1))
            if page_match
            else None,
            excerpt=(
                excerpt.strip()[:MAX_SOURCE_EXCERPT_CHARS]
                if isinstance(excerpt, str) and excerpt.strip()
                else None
            ),
            score=float(score) if isinstance(score, (int, float)) else None,
        )
