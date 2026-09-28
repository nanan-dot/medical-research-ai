"""Register observed document bytes and propagate version changes safely."""

from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_relocation.model import AssetAnchorLink, DocumentFileRevision


class FileVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def observe(
        self, document: Document, *, content_available: bool = False
    ) -> DocumentFileRevision:
        """Persist current metadata and invalidate only locations tied to older bytes."""
        # 文件版本与 A0 请求共享同一文档级写栅栏，避免并发首次请求各自创建 current 行。
        await self._session.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(file_hash=Document.file_hash)
        )
        current = await self._session.scalar(
            select(DocumentFileRevision).where(
                DocumentFileRevision.document_id == document.id,
                DocumentFileRevision.is_current.is_(True),
            )
        )
        if current is not None and current.file_hash == document.file_hash:
            return current
        now = datetime.now(UTC)
        if current is not None:
            current.is_current = False
            current.superseded_at = now
        existing = await self._session.scalar(
            select(DocumentFileRevision).where(
                DocumentFileRevision.document_id == document.id,
                DocumentFileRevision.file_hash == document.file_hash,
            )
        )
        revision = existing or DocumentFileRevision(
            document_id=document.id,
            file_hash=document.file_hash,
            file_size=document.file_size,
            modified_time_ns=document.modified_time_ns,
            storage_kind="managed" if content_available else "external",
            storage_reference=None,
            is_content_available=content_available,
            retention_status="retained" if content_available else "metadata_only",
        )
        revision.is_current = True
        revision.superseded_at = None
        if existing is None:
            self._session.add(revision)
        await self._session.flush()
        stale_ids = list(
            (
                await self._session.scalars(
                    select(DocumentAnchorRevision.id).where(
                        DocumentAnchorRevision.document_id == document.id,
                        DocumentAnchorRevision.file_hash != document.file_hash,
                        DocumentAnchorRevision.state.in_(("ready", "review_required")),
                    )
                )
            ).all()
        )
        if stale_ids:
            await self._session.execute(
                update(DocumentAnchorRevision)
                .where(DocumentAnchorRevision.id.in_(stale_ids))
                .values(state="stale")
            )
            old_anchor_ids = select(DocumentSourceAnchor.id).where(
                DocumentSourceAnchor.anchor_revision_id.in_(stale_ids)
            )
            await self._session.execute(
                update(AssetAnchorLink)
                .where(
                    or_(
                        AssetAnchorLink.original_anchor_id.in_(old_anchor_ids),
                        AssetAnchorLink.resolved_anchor_id.in_(old_anchor_ids),
                    )
                )
                .values(
                    resolved_anchor_id=None,
                    resolution_status="relocation_required",
                    resolution_version=AssetAnchorLink.resolution_version + 1,
                )
            )
        return revision


__all__ = ["FileVersionService"]
