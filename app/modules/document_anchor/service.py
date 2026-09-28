"""A0 API 编排与短事务发布；解析期间不持有数据库事务。"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.modules.document_anchor.extractor_runner import PdfTextItemExtractor
from app.modules.document_anchor.fingerprint import request_fingerprint
from app.modules.document_anchor.input_validation import verify_pdf
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.page_builder import page_entities as _page_entities
from app.modules.document_anchor.publisher import Extraction, publish
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_anchor.repository import DocumentAnchorRepository
from app.modules.document_anchor.schema import (
    AnchorManifestRead,
    AnchorRevisionRead,
    AnchorRevisionRequest,
    SourcePageQualityRead,
)
from app.modules.document_anchor.staging import StagedExtraction
from app.modules.document_anchor.toolchain import (
    EXTRACTOR_VERSION,
    NORMALIZATION_VERSION,
    OPTIONS_HASH,
    PDFJS_VERSION,
    identity,
)
from app.modules.document_preview.service import DocumentPreviewService
from app.modules.document_relocation.file_versions import FileVersionService
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository

TASK_TYPE = "document_anchor_extraction"
VISIBLE = {"ready", "review_required", "stale"}
_PROBE_TTL_SECONDS = 30.0
_probe_cache: tuple[str, float] | None = None
_probe_lock = asyncio.Lock()
__all__ = ["OPTIONS_HASH", "TASK_TYPE", "DocumentAnchorService", "_page_entities"]


class AnchorRevisionConflictError(ConflictError):
    code = "anchor_revision_conflict"


class AnchorLeaseLostError(RuntimeError):
    """Task was cancelled or another worker owns its lease."""


async def _ensure_toolchain_available() -> None:
    """Coalesce short-lived request probes; execution still validates its own stream."""
    global _probe_cache
    command = settings.PDF_TEXTITEM_EXTRACTOR_COMMAND
    now = monotonic()
    if _probe_cache and _probe_cache[0] == command and now - _probe_cache[1] < _PROBE_TTL_SECONDS:
        return
    async with _probe_lock:
        now = monotonic()
        if _probe_cache and _probe_cache[0] == command and now - _probe_cache[1] < _PROBE_TTL_SECONDS:
            return
        await PdfTextItemExtractor().probe()
        _probe_cache = (command, monotonic())


class DocumentAnchorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._queries = AnchorQueries(session)
        self._anchors = DocumentAnchorRepository(session)
        self._tasks = TaskRepository(session)

    async def request(
        self,
        document_id: int,
        payload: AnchorRevisionRequest,
        idempotency_key: str | None = None,
    ) -> AnchorRevisionRead:
        document = await self._queries.authorized_document(document_id)
        file_hash = document.file_hash
        if file_hash != payload.expected_file_hash:
            raise AnchorRevisionConflictError("Document file version has changed")
        path = await DocumentPreviewService(self._session).get_pdf_path(document_id)
        await asyncio.to_thread(verify_pdf, path, file_hash)
        request_hash = request_fingerprint(
            file_hash,
            EXTRACTOR_VERSION,
            PDFJS_VERSION,
            NORMALIZATION_VERSION,
            OPTIONS_HASH,
        )
        file_revision = await FileVersionService(self._session).observe(document)
        revision = await self._anchors.get_by_request(document_id, request_hash)
        if (
            revision
            and revision.state in {"ready", "review_required"}
            and not payload.force_new_toolchain_run
        ):
            return self._queries.revision_read(revision)
        await _ensure_toolchain_available()
        # SAVEPOINT 只回滚竞争插入，不能丢失请求事务中其他已完成的工作。
        if revision is None:
            try:
                async with self._session.begin_nested():
                    revision = await self._anchors.create_revision(
                        DocumentAnchorRevision(
                            document_id=document_id,
                            document_file_revision_id=file_revision.id,
                            file_hash=file_hash,
                            request_fingerprint=request_hash,
                            extractor_version=EXTRACTOR_VERSION,
                            pdfjs_version=PDFJS_VERSION,
                            normalization_version=NORMALIZATION_VERSION,
                            options_hash=OPTIONS_HASH,
                            state="pending",
                        )
                    )
            except IntegrityError:
                revision = await self._anchors.get_by_request(document_id, request_hash)
                if revision is None:
                    raise
        task = await self._enqueue_task(
            document_id,
            revision.id,
            request_hash,
            payload.force_new_toolchain_run,
            idempotency_key,
        )
        if revision.extraction_fingerprint is None and revision.state in {
            "failed",
            "cancelled",
        }:
            revision.state = "pending"
            revision.error_code = revision.error_message = None
            revision.finished_at = None
        return self._queries.revision_read(revision, task.id)

    async def manifest(self, document_id: int) -> AnchorManifestRead:
        return await self._queries.manifest(document_id)

    async def get_revision(self, revision_id: int) -> AnchorRevisionRead:
        return await self._queries.get_revision(revision_id)

    async def page_quality(
        self, document_id: int, revision_id: int, page_number: int
    ) -> SourcePageQualityRead:
        return await self._queries.page_quality(document_id, revision_id, page_number)

    async def text_items(
        self,
        document_id: int,
        revision_id: int,
        page_number: int,
        start: int = 0,
        limit: int = 200,
    ) -> list[DocumentSourceTextItem]:
        return await self._queries.text_items(
            document_id, revision_id, page_number, start, limit
        )

    async def execute(
        self,
        revision_id: int,
        extractor: PdfTextItemExtractor | None = None,
        task_id: int | None = None,
        worker_id: str | None = None,
    ) -> None:
        revision = await self._anchors.get_revision(revision_id)
        if revision is None:
            raise NotFoundError("Anchor revision not found")
        document_id, file_hash = revision.document_id, revision.file_hash
        is_diagnostic = revision.extraction_fingerprint is not None
        stream: Extraction | None = None
        try:
            await self._fence(task_id, worker_id, phase="extracting")
            document = await self._queries.authorized_document(document_id)
            if document.file_hash != file_hash:
                raise AnchorRevisionConflictError("Document file version has changed")
            path = await DocumentPreviewService(self._session).get_pdf_path(document_id)
            if not is_diagnostic:
                revision.state = "extracting"
            await self._session.commit()
            # 子进程、暂存文件和数据库发布各自承担单一职责；取消/心跳使用独立会话。
            stream = await (extractor or PdfTextItemExtractor()).extract(
                path, file_hash, str(uuid4())
            )
            self._validate_stream_toolchain(stream)
            await asyncio.to_thread(verify_pdf, path, file_hash)
            await self._fence(task_id, worker_id, phase="publishing")
            await self._session.commit()
            document = await self._queries.authorized_document(document_id, fresh=True)
            final_path = await DocumentPreviewService(self._session).get_pdf_path(
                document_id
            )
            if final_path != path:
                raise AnchorRevisionConflictError(
                    "Document asset changed during extraction"
                )
            revision = await self._anchors.get_revision(revision_id)
            if revision is not None:
                await self._session.refresh(revision)
            if (
                revision is None
                or document.file_hash != file_hash
                or stream.header.file_sha256 != file_hash
            ):
                raise AnchorRevisionConflictError("Document file version has changed")
            await publish(self._session, revision, stream)
            # A0 publication and durable A1 enqueue form one transaction.  If
            # enqueue fails, the leased A0 task remains retryable instead of
            # being stranded in a false succeeded state.
            if task_id is not None:
                from app.modules.document_layout.service import DocumentLayoutService

                await DocumentLayoutService(self._session).request(revision_id)
            if task_id is not None:
                result = await self._session.execute(
                    update(TaskRecord)
                    .where(
                        TaskRecord.id == task_id,
                        TaskRecord.status == "running",
                        TaskRecord.lease_owner == worker_id,
                        TaskRecord.lease_expires_at > datetime.now(UTC),
                    )
                    .values(
                        status="succeeded",
                        progress=100,
                        phase="completed",
                        completed_units=len(stream.pages),
                        total_units=len(stream.pages),
                        current_item=None,
                        active_idempotency_key=None,
                        lease_owner=None,
                        lease_expires_at=None,
                        error_code=None,
                        error_message=None,
                        finished_at=datetime.now(UTC),
                    )
                )
                if getattr(result, "rowcount", 0) != 1:
                    raise AnchorLeaseLostError("Anchor task lease is no longer owned")
            await self._session.commit()
        except BaseException as exc:
            await self._session.rollback()
            # worker 通过带租约条件的终态事务处理失败；过期 worker 不能覆盖新 worker。
            if task_id is None and not is_diagnostic:
                await self._session.execute(
                    update(DocumentAnchorRevision)
                    .where(
                        DocumentAnchorRevision.id == revision_id,
                        DocumentAnchorRevision.extraction_fingerprint.is_(None),
                    )
                    .values(
                        state="cancelled"
                        if isinstance(exc, asyncio.CancelledError)
                        else "failed",
                        error_code=getattr(exc, "code", "anchor_extraction_failed"),
                        error_message="PDF TextItem extraction did not complete",
                        finished_at=datetime.now(UTC),
                    )
                )
                await self._session.commit()
            raise
        finally:
            if isinstance(stream, StagedExtraction):
                stream.close()

    async def _fence(
        self, task_id: int | None, worker_id: str | None, *, phase: str
    ) -> None:
        if task_id is None:
            return
        result = await self._session.execute(
            update(TaskRecord)
            .where(
                TaskRecord.id == task_id,
                TaskRecord.status == "running",
                TaskRecord.lease_owner == worker_id,
                TaskRecord.lease_expires_at > datetime.now(UTC),
            )
            .values(phase=phase)
        )
        if getattr(result, "rowcount", 0) != 1:
            raise AnchorLeaseLostError("Anchor task lease is no longer owned")

    async def _enqueue_task(
        self,
        document_id: int,
        revision_id: int,
        request_hash: str,
        diagnostic: bool,
        client_key: str | None,
    ) -> TaskRecord:
        key = f"anchor:{document_id}:{request_hash}"
        active = await self._tasks.find_active_by_key(key)
        if active is not None:
            return active
        detail = {
            "revision_id": revision_id,
            "operation": "anchor_extraction",
            "diagnostic": diagnostic,
            "client_idempotency_key": client_key,
            "limits_json": json.dumps(
                {
                    "max_pages": settings.PDF_TEXTITEM_EXTRACTOR_MAX_PAGES,
                    "max_items": settings.PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE,
                    "max_output_bytes": settings.PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES,
                    "timeout_seconds": settings.PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS,
                }
            ),
        }
        task = TaskRecord(
            task_type=TASK_TYPE,
            title="Document anchor extraction",
            status="queued",
            source_type="document",
            source_id=document_id,
            detail_json=json.dumps(detail),
            idempotency_key=key,
            active_idempotency_key=key,
        )
        try:
            async with self._session.begin_nested():
                return await self._tasks.create(task)
        except IntegrityError:
            existing = await self._tasks.find_active_by_key(key)
            if existing is None:
                raise
            return existing

    @staticmethod
    def _validate_stream_toolchain(stream: Extraction) -> None:
        if any(
            getattr(stream.header, key) != value for key, value in identity().items()
        ):
            raise AnchorRevisionConflictError("Extractor toolchain identity mismatch")
