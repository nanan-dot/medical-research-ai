"""Database access for paper analyses."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.paper_analysis.model import PaperAnalysis


class PaperAnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> PaperAnalysis | None:
        return await self.session.get(PaperAnalysis, id)

    async def create(self, entity: PaperAnalysis) -> PaperAnalysis:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def save(self, entity: PaperAnalysis) -> PaperAnalysis:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def latest_for_document(self, document_id: int) -> PaperAnalysis | None:
        result = await self.session.execute(
            select(PaperAnalysis)
            .where(PaperAnalysis.document_id == document_id)
            .order_by(PaperAnalysis.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
