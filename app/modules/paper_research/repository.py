"""Read models for the paper-research workspace."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.model import Conversation, Message
from app.modules.document.model import Document
from app.modules.document_upload.model import DocumentAsset
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis


class PaperResearchRepository:
    """Execute bounded aggregate queries without per-row relationship loading."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _library_column(column):
        return (
            select(column)
            .where(LibraryItem.document_id == Document.id)
            .order_by(LibraryItem.id.asc())
            .limit(1)
            .scalar_subquery()
        )

    @staticmethod
    def _original_filename():
        return (
            select(DocumentAsset.original_filename)
            .where(DocumentAsset.document_id == Document.id)
            .limit(1)
            .scalar_subquery()
        )

    def _document_columns(self):
        library_title = self._library_column(LibraryItem.title)
        title = func.coalesce(
            library_title,
            Document.parsed_title,
            self._original_filename(),
            Document.file_path,
        )
        return (
            title.label("title"),
            self._library_column(LibraryItem.year).label("year"),
            self._library_column(LibraryItem.pmid).label("pmid"),
        )

    @staticmethod
    def _indexed_filter():
        return (
            Document.index_status == "succeeded",
            Document.paperqa_index_key.is_not(None),
        )

    async def indexed_documents(
        self, q: str | None, offset: int, limit: int
    ) -> tuple[list[tuple[Document, str, int | None, str | None]], int]:
        title, year, pmid = self._document_columns()
        statement = select(Document, title, year, pmid).where(*self._indexed_filter())
        count_statement = (
            select(func.count()).select_from(Document).where(*self._indexed_filter())
        )
        if q:
            pattern = f"%{q.casefold()}%"
            search_filter = or_(
                func.lower(title).like(pattern), func.lower(pmid).like(pattern)
            )
            statement = statement.where(search_filter)
            count_statement = count_statement.where(search_filter)
        result = await self.session.execute(
            statement.order_by(func.lower(title), Document.id)
            .offset(offset)
            .limit(limit)
        )
        total = await self.session.scalar(count_statement)
        documents: list[tuple[Document, str, int | None, str | None]] = list(
            result.tuples().all()
        )
        return documents, int(total or 0)

    async def recent_analyses(self, limit: int):
        title, _, _ = self._document_columns()
        result = await self.session.execute(
            select(PaperAnalysis, title)
            .join(Document, Document.id == PaperAnalysis.document_id)
            .where(PaperAnalysis.analysis_status == "succeeded")
            .order_by(PaperAnalysis.updated_at.desc(), PaperAnalysis.id.desc())
            .limit(limit)
        )
        return list(result.all())

    async def analyses_with_pending_confirmations(self, limit: int):
        title, _, _ = self._document_columns()
        result = await self.session.execute(
            select(PaperAnalysis, title)
            .join(Document, Document.id == PaperAnalysis.document_id)
            .where(
                PaperAnalysis.analysis_status == "succeeded",
                PaperAnalysis.pending_confirmations.is_not(None),
            )
            .order_by(PaperAnalysis.updated_at.desc(), PaperAnalysis.id.desc())
            .limit(limit)
        )
        return list(result.all())

    async def recent_conversations(self, limit: int):
        message_counts = (
            select(
                Message.conversation_id.label("conversation_id"),
                func.count(Message.id).label("message_count"),
            )
            .group_by(Message.conversation_id)
            .subquery()
        )
        result = await self.session.execute(
            select(Conversation, func.coalesce(message_counts.c.message_count, 0))
            .outerjoin(
                message_counts, message_counts.c.conversation_id == Conversation.id
            )
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
        )
        return list(result.all())
