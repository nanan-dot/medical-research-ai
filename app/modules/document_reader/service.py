"""阅读会话、位置、exposure 与进度业务。"""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_layout.model import DocumentSegmentationRevision
from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.document_reader.errors import (
    DocumentFileChangedError,
    ReaderResourceNotFoundError,
    ReaderStateVersionConflictError,
)
from app.modules.document_reader.idempotency import ensure_payload_matches
from app.modules.document_reader.model import ReaderPageExposure, ReaderSession
from app.modules.document_reader.progress import (
    ExposureFact,
    merge_exposure,
    project_progress,
)
from app.modules.document_reader.repository import ReaderRepository
from app.modules.document_reader.schema import (
    ExposureBatchCreate,
    ProgressRead,
    ReaderPositionUpdate,
    SessionCreate,
    SessionRead,
)
from app.modules.library_item.model import LibraryItem


class ReaderSessionService:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope
        self._repo = ReaderRepository(session)

    async def create_or_reuse(self, library_item_id: int, payload: SessionCreate, idempotency_key: str) -> SessionRead:
        item, document = await self._item_document(library_item_id)
        payload_hash = self._payload_hash(library_item_id, payload)
        if idempotency_key:
            idempotent = await self._repo.session_by_idempotency_key(idempotency_key, self._actor_scope)
            if idempotent is not None:
                ensure_payload_matches(idempotent.idempotency_payload_hash or "", payload_hash)
                return self._read(idempotent)
        existing = await self._repo.active_session(
            item.id, payload.device_id, self._actor_scope, document.file_hash
        )
        if existing is not None:
            return self._read(existing)
        anchor = await self._current_anchor(document.id)
        segmentation = await self._current_segmentation(anchor.id) if anchor else None
        entity = ReaderSession(actor_scope=self._actor_scope, library_item_id=item.id, document_id=document.id, document_file_hash=document.file_hash, anchor_revision_id=anchor.id if anchor else None, segmentation_revision_id=segmentation.id if segmentation else None, device_id=payload.device_id, idempotency_key=idempotency_key or None, idempotency_payload_hash=payload_hash, last_page=1, viewport_offset_ratio=0, status="active", version=1)
        await self._repo.save(entity)
        return self._read(entity)

    async def update_position(self, session_id: int, payload: ReaderPositionUpdate) -> SessionRead:
        entity = await self._require_session(session_id)
        document = await self._session.get(Document, entity.document_id)
        if document is None:
            raise ReaderResourceNotFoundError("文档不存在")
        if document.file_hash != payload.expected_file_hash or entity.document_file_hash != document.file_hash:
            raise DocumentFileChangedError("PDF 已换版，请重新打开阅读器")
        if payload.expected_version != entity.version:
            raise ReaderStateVersionConflictError({"page": entity.last_page, "viewport_offset_ratio": entity.viewport_offset_ratio, "version": entity.version})
        if document.parsed_page_count and payload.page > document.parsed_page_count:
            raise ValueError("page exceeds document page count")
        await self._validate_session_anchor(entity, payload.source_anchor_id)
        entity.last_page = payload.page
        entity.viewport_offset_ratio = payload.viewport_offset_ratio
        entity.last_anchor_id = payload.source_anchor_id
        entity.last_seen_at = datetime.now(UTC)
        entity.version += 1
        await self._repo.save(entity)
        return self._read(entity)

    async def add_exposures(self, session_id: int, payload: ExposureBatchCreate) -> ProgressRead:
        entity = await self._require_session(session_id)
        document = await self._session.get(Document, entity.document_id)
        if document is None:
            raise ReaderResourceNotFoundError("文档不存在")
        if payload.expected_file_hash and payload.expected_file_hash != document.file_hash:
            raise DocumentFileChangedError("PDF 已换版，请重新打开阅读器")
        total_pages = document.parsed_page_count or 0
        for item in payload.exposures:
            if total_pages and item.page_number > total_pages:
                raise ValueError("page exceeds document page count")
            current = await self._repo.exposure(entity.id, item.page_number)
            if current is None:
                fact = merge_exposure(ExposureFact(item.page_number, 0, 0, None), visible_milliseconds=item.visible_milliseconds, max_visible_ratio=item.max_visible_ratio)
                current = ReaderPageExposure(session_id=entity.id, page_number=item.page_number, first_visible_at=item.first_visible_at, last_visible_at=item.last_visible_at, visible_milliseconds=fact.visible_milliseconds, max_visible_ratio=fact.max_visible_ratio, qualified_at=fact.qualified_at)
            else:
                fact = merge_exposure(ExposureFact(current.page_number, current.visible_milliseconds, current.max_visible_ratio, current.qualified_at), visible_milliseconds=item.visible_milliseconds, max_visible_ratio=item.max_visible_ratio)
                current.last_visible_at = max(current.last_visible_at, item.last_visible_at)
                current.first_visible_at = min(current.first_visible_at, item.first_visible_at)
                current.visible_milliseconds = fact.visible_milliseconds
                current.max_visible_ratio = fact.max_visible_ratio
                current.qualified_at = fact.qualified_at
            await self._repo.save(current)
        return await self.progress(entity.library_item_id)

    async def progress(self, library_item_id: int) -> ProgressRead:
        _, document = await self._item_document(library_item_id)
        rows = await self._repo.exposures_for_item(
            library_item_id, self._actor_scope, document.file_hash
        )
        projection = project_progress([ExposureFact(row.page_number, row.visible_milliseconds, row.max_visible_ratio, row.qualified_at) for row in rows], document.parsed_page_count or 0)
        return ProgressRead(
            qualified_pages=projection.qualified_pages,
            total_pages=projection.total_pages,
            percent=projection.percent,
        )

    async def close(self, session_id: int, reason: str = "user") -> SessionRead:
        entity = await self._require_session(session_id)
        if entity.status not in ("closed", "abandoned"):
            entity.status = "closed"
            entity.close_reason = reason
            entity.ended_at = datetime.now(UTC)
            entity.version += 1
            await self._repo.save(entity)
        return self._read(entity)

    async def _require_session(self, session_id: int) -> ReaderSession:
        entity = await self._repo.get_session(session_id, self._actor_scope)
        if entity is None:
            raise ReaderResourceNotFoundError("阅读会话不存在")
        return entity

    async def _validate_session_anchor(
        self, reader_session: ReaderSession, source_anchor_id: int | None
    ) -> None:
        """Reject positions pointing at an anchor outside the session's frozen revision."""
        if source_anchor_id is None:
            return
        source_anchor = await self._session.get(DocumentSourceAnchor, source_anchor_id)
        if (
            source_anchor is None
            or source_anchor.anchor_revision_id != reader_session.anchor_revision_id
        ):
            raise ReaderResourceNotFoundError("SourceAnchor 不属于该阅读会话的 revision")

    async def _item_document(self, item_id: int) -> tuple[LibraryItem, Document]:
        item = await self._session.get(LibraryItem, item_id)
        if item is None or item.document_id is None:
            raise ReaderResourceNotFoundError("论文或其 PDF 不存在")
        document = await self._session.get(Document, item.document_id)
        if document is None:
            raise ReaderResourceNotFoundError("论文 PDF 不存在")
        return item, document

    async def _current_anchor(self, document_id: int) -> DocumentAnchorRevision | None:
        return await self._session.scalar(select(DocumentAnchorRevision).where(DocumentAnchorRevision.document_id == document_id, DocumentAnchorRevision.state.in_(("ready", "review_required"))))

    async def _current_segmentation(self, anchor_id: int) -> DocumentSegmentationRevision | None:
        return await self._session.scalar(select(DocumentSegmentationRevision).where(DocumentSegmentationRevision.anchor_revision_id == anchor_id, DocumentSegmentationRevision.state.in_(("ready", "review_required"))))

    @staticmethod
    def _payload_hash(library_item_id: int, payload: SessionCreate) -> str:
        canonical = {"library_item_id": library_item_id, **payload.model_dump(mode="json")}
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _read(entity: ReaderSession) -> SessionRead:
        return SessionRead(id=entity.id, paper_item_id=entity.library_item_id, document_id=entity.document_id, file_hash=entity.document_file_hash, page=entity.last_page, viewport_offset_ratio=entity.viewport_offset_ratio, status=entity.status, version=entity.version)
