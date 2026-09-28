"""A0-only persistence queries; business decisions remain in the service."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)


class DocumentAnchorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_revision(self, revision_id: int) -> DocumentAnchorRevision | None:
        return await self._session.get(DocumentAnchorRevision, revision_id)

    async def get_for_document(
        self, document_id: int, revision_id: int
    ) -> DocumentAnchorRevision | None:
        return await self._session.scalar(
            select(DocumentAnchorRevision).where(
                DocumentAnchorRevision.id == revision_id,
                DocumentAnchorRevision.document_id == document_id,
            )
        )

    async def get_by_request(
        self, document_id: int, request_hash: str
    ) -> DocumentAnchorRevision | None:
        return await self._session.scalar(
            select(DocumentAnchorRevision).where(
                DocumentAnchorRevision.document_id == document_id,
                DocumentAnchorRevision.request_fingerprint == request_hash,
            )
        )

    async def latest_visible(self, document_id: int) -> DocumentAnchorRevision | None:
        return await self._session.scalar(
            select(DocumentAnchorRevision)
            .where(
                DocumentAnchorRevision.document_id == document_id,
                DocumentAnchorRevision.state.in_(("ready", "review_required")),
            )
            .order_by(DocumentAnchorRevision.id.desc())
            .limit(1)
        )

    async def create_revision(
        self, revision: DocumentAnchorRevision
    ) -> DocumentAnchorRevision:
        self._session.add(revision)
        await self._session.flush()
        await self._session.refresh(revision)
        return revision

    async def page_quality(
        self, revision_id: int, page_number: int
    ) -> DocumentSourcePage | None:
        return await self._session.scalar(
            select(DocumentSourcePage).where(
                DocumentSourcePage.revision_id == revision_id,
                DocumentSourcePage.page_number == page_number,
            )
        )

    async def stale_other_visible(self, document_id: int, revision_id: int) -> None:
        await self._session.execute(
            update(DocumentAnchorRevision)
            .where(
                DocumentAnchorRevision.document_id == document_id,
                DocumentAnchorRevision.id != revision_id,
                DocumentAnchorRevision.state.in_(("ready", "review_required")),
            )
            .values(state="stale")
        )

    async def text_items(
        self, page_id: int, start: int, limit: int
    ) -> list[DocumentSourceTextItem]:
        return list(
            (
                await self._session.scalars(
                    select(DocumentSourceTextItem)
                    .where(
                        DocumentSourceTextItem.page_id == page_id,
                        DocumentSourceTextItem.item_index >= start,
                    )
                    .order_by(DocumentSourceTextItem.item_index)
                    .limit(limit)
                )
            ).all()
        )
