"""Product-facing PaperQA2 indexing orchestration."""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.common.hashing import sha256_file
from app.core.config import settings
from app.integrations.paperqa2 import PaperDocument, PaperQA2Client, create_paperqa2_client
from app.integrations.paperqa2.exceptions import PaperQA2Error
from app.modules.document.model import Document
from app.modules.document.schema import (
    BatchIndexResult,
    DocumentIndexResult,
    IndexStatus,
    ParseStatus,
)
from app.modules.document.service import DocumentService, sanitize_error_message

_DOCUMENT_LOCKS: dict[int, asyncio.Lock] = {}


class DocumentIndexService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], PaperQA2Client] | None = None,
        index_root: Path | None = None,
        paperqa_version: str | None = None,
    ):
        self.documents = DocumentService(session)
        self.client_factory = client_factory or create_paperqa2_client
        self.index_root = (index_root or settings.PAPERQA_INDEX_DIR).resolve()
        self.paperqa_version = paperqa_version or settings.PAPERQA_VERSION

    async def index(self, document_id: int) -> DocumentIndexResult:
        lock = _DOCUMENT_LOCKS.setdefault(document_id, asyncio.Lock())
        if lock.locked():
            raise ConflictError("Document indexing is already running")
        async with lock:
            return await self._index_locked(document_id)

    async def _index_locked(self, document_id: int) -> DocumentIndexResult:
        document = await self.documents.get(document_id)
        if document.parse_status != ParseStatus.SUCCEEDED.value:
            raise ConflictError("Document must be parsed successfully before indexing")
        path = await self.documents._source_file_path(document)
        current_hash = await asyncio.to_thread(sha256_file, path)
        if current_hash != document.file_hash:
            document.index_status = IndexStatus.OUTDATED.value
            document.index_error = "Source file changed after the last synchronization"
            await self.documents.repo.save(document)
            raise ConflictError("Document changed and must be synchronized before indexing")

        if (
            document.index_status == IndexStatus.SUCCEEDED.value
            and document.indexed_hash == document.file_hash
            and document.paperqa_version == self.paperqa_version
            and document.paperqa_index_key
        ):
            return self._result(document, reused=True)

        needs_rebuild = bool(
            document.paperqa_index_key
            or document.index_status == IndexStatus.OUTDATED.value
            or document.indexed_hash != document.file_hash
            or document.paperqa_version != self.paperqa_version
        )
        await self._prepare_for_index(document)
        try:
            namespace = self._prepare_namespace(document)
            client = self.client_factory()
            index = await client.index_documents(
                [PaperDocument(path=path, title=document.parsed_title)],
                rebuild=needs_rebuild,
            )
        except ConflictError as exc:
            await self._mark_failed(document, "index_namespace_conflict", str(exc))
            raise
        except PaperQA2Error as exc:
            await self._mark_failed(document, exc.code, exc.message)
            raise ConflictError(exc.message) from exc
        except Exception as exc:
            await self._mark_failed(document, "paperqa2_operation_error", "PaperQA2 indexing failed")
            raise ConflictError("PaperQA2 indexing failed") from exc

        document.paperqa_index_key = index.index_id
        document.paperqa_version = self.paperqa_version
        document.indexed_hash = document.file_hash
        document.index_error = None
        await self.documents.mark_index_status(document, IndexStatus.SUCCEEDED)
        self._write_marker(namespace, document)
        return self._result(document, reused=index.reused)

    async def batch_index(self, document_ids: list[int]) -> BatchIndexResult:
        results: list[DocumentIndexResult] = []
        for document_id in dict.fromkeys(document_ids):
            try:
                results.append(await self.index(document_id))
            except Exception as exc:
                results.append(
                    DocumentIndexResult(
                        document_id=document_id,
                        index_status=IndexStatus.FAILED,
                        paperqa_index_key=None,
                        paperqa_version=self.paperqa_version,
                        indexed_hash=None,
                        reused=False,
                        error_code=getattr(exc, "code", "index_failed"),
                        error_message=sanitize_error_message(str(exc)),
                    )
                )
        failed = sum(result.index_status == IndexStatus.FAILED for result in results)
        return BatchIndexResult(results=results, succeeded=len(results) - failed, failed=failed)

    async def delete_index(self, document_id: int) -> DocumentIndexResult:
        document = await self.documents.get(document_id)
        if document.index_status == IndexStatus.INDEXING.value:
            raise ConflictError("Cannot delete an index while indexing is running")
        namespace = self.index_root / f"document-{document.id}"
        marker = namespace / "metadata.json"
        if marker.is_file():
            marker.unlink()
        if namespace.is_dir():
            try:
                namespace.rmdir()
            except OSError:
                pass
        document.paperqa_index_key = None
        document.paperqa_version = None
        document.indexed_hash = None
        document.index_error = None
        await self.documents.delete_index(document_id)
        return self._result(document, reused=False)

    async def _prepare_for_index(self, document: Document) -> None:
        current = IndexStatus(document.index_status)
        if current == IndexStatus.INDEXING:
            raise ConflictError("Document indexing is already running")
        if current == IndexStatus.SUCCEEDED:
            await self.documents.mark_index_status(document, IndexStatus.OUTDATED)
            current = IndexStatus.OUTDATED
        if current in {IndexStatus.FAILED, IndexStatus.OUTDATED}:
            await self.documents.mark_index_status(document, IndexStatus.PENDING)
        await self.documents.mark_index_status(document, IndexStatus.INDEXING)

    def _prepare_namespace(self, document: Document) -> Path:
        self.index_root.mkdir(parents=True, exist_ok=True)
        namespace = (self.index_root / f"document-{document.id}").resolve()
        if namespace.parent != self.index_root:
            raise ConflictError("PaperQA2 index namespace is invalid")
        namespace.mkdir(exist_ok=True)
        marker = namespace / "metadata.json"
        if marker.is_file():
            try:
                metadata = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ConflictError("PaperQA2 index metadata is incompatible") from exc
            if metadata.get("document_id") != document.id:
                raise ConflictError("PaperQA2 index namespace conflicts with another document")
        return namespace

    @staticmethod
    def _write_marker(namespace: Path, document: Document) -> None:
        marker = namespace / "metadata.json"
        temporary = namespace / "metadata.json.tmp"
        temporary.write_text(
            json.dumps(
                {
                    "document_id": document.id,
                    "index_key": document.paperqa_index_key,
                    "paperqa_version": document.paperqa_version,
                    "indexed_hash": document.indexed_hash,
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(marker)

    async def _mark_failed(self, document: Document, code: str, message: str) -> None:
        document.index_error = sanitize_error_message(message)
        await self.documents.mark_index_status(document, IndexStatus.FAILED, code, message)

    @staticmethod
    def _result(document: Document, *, reused: bool) -> DocumentIndexResult:
        return DocumentIndexResult(
            document_id=document.id,
            index_status=IndexStatus(document.index_status),
            paperqa_index_key=document.paperqa_index_key,
            paperqa_version=document.paperqa_version,
            indexed_hash=document.indexed_hash,
            reused=reused,
            error_code=document.error_code,
            error_message=document.index_error,
        )
