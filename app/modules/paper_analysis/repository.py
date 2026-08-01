"""paper_analysis — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.paper_analysis.model import PaperAnalysis


class PaperAnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> PaperAnalysis | None:
        result = await self.session.execute(
            select(PaperAnalysis).where(PaperAnalysis.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[PaperAnalysis]:
        result = await self.session.execute(
            select(PaperAnalysis).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: PaperAnalysis) -> PaperAnalysis:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: PaperAnalysis) -> None:
        await self.session.delete(entity)
        await self.session.flush()
