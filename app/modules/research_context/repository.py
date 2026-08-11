"""Database access isolated to research-context records and links."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research_context.model import ResearchContext, ResearchContextDocument


class ResearchContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: ResearchContext) -> ResearchContext:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get(self, context_id: int) -> ResearchContext | None:
        return await self.session.get(ResearchContext, context_id)

    async def list_contexts(self) -> list[ResearchContext]:
        result = await self.session.execute(
            select(ResearchContext).order_by(ResearchContext.updated_at.desc())
        )
        return list(result.scalars())

    async def documents(self, context_id: int) -> list[ResearchContextDocument]:
        result = await self.session.execute(
            select(ResearchContextDocument)
            .where(ResearchContextDocument.research_context_id == context_id)
            .order_by(ResearchContextDocument.document_id)
        )
        return list(result.scalars())

    async def document_link(
        self, context_id: int, document_id: int
    ) -> ResearchContextDocument | None:
        result = await self.session.execute(
            select(ResearchContextDocument).where(
                ResearchContextDocument.research_context_id == context_id,
                ResearchContextDocument.document_id == document_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_document(self, entity: ResearchContextDocument) -> None:
        self.session.add(entity)
        await self.session.flush()

    async def save(self) -> None:
        await self.session.flush()
