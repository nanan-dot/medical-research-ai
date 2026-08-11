"""Business orchestration for paper-research aggregate reads."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.paper_research.repository import PaperResearchRepository
from app.modules.paper_research.schema import (
    IndexedDocumentPage,
    IndexedDocumentRead,
    PaperResearchOverviewRead,
    PendingConfirmationRead,
    RecentAnalysisRead,
    RecentConversationRead,
)


class PaperResearchService:
    """Expose UI-oriented projections while preserving source-of-truth modules."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = PaperResearchRepository(session)

    async def indexed_documents(
        self, q: str | None, offset: int, limit: int
    ) -> IndexedDocumentPage:
        documents, total = await self.repository.indexed_documents(q, offset, limit)
        return IndexedDocumentPage(
            items=[
                IndexedDocumentRead(
                    document_id=document.id, title=title, year=year, pmid=pmid
                )
                for document, title, year, pmid in documents
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def overview(
        self, analysis_limit: int, pending_limit: int, conversation_limit: int
    ) -> PaperResearchOverviewRead:
        analyses = await self.repository.recent_analyses(analysis_limit)
        pending_analyses = await self.repository.analyses_with_pending_confirmations(
            pending_limit
        )
        conversations = await self.repository.recent_conversations(conversation_limit)
        return PaperResearchOverviewRead(
            recent_analyses=[
                RecentAnalysisRead(
                    analysis_id=analysis.id,
                    document_id=analysis.document_id,
                    title=title,
                    updated_at=analysis.updated_at,
                )
                for analysis, title in analyses
            ],
            pending_confirmations=self._pending_confirmations(pending_analyses),
            recent_conversations=[
                RecentConversationRead(
                    id=conversation.id,
                    document_ids=json.loads(conversation.document_ids),
                    title=conversation.title,
                    updated_at=conversation.updated_at,
                    message_count=message_count,
                )
                for conversation, message_count in conversations
            ],
        )

    @staticmethod
    def _pending_confirmations(pending_analyses):
        items: list[PendingConfirmationRead] = []
        for analysis, title in pending_analyses:
            for field_name in json.loads(analysis.pending_confirmations or "[]"):
                items.append(
                    PendingConfirmationRead(
                        analysis_id=analysis.id,
                        document_id=analysis.document_id,
                        title=title,
                        field_name=field_name,
                        updated_at=analysis.updated_at,
                    )
                )
        return items
