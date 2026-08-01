"""research_direction — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.research_direction.model import ResearchDirection


class ResearchDirectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> ResearchDirection | None:
        result = await self.session.execute(
            select(ResearchDirection).where(ResearchDirection.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[ResearchDirection]:
        result = await self.session.execute(
            select(ResearchDirection).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: ResearchDirection) -> ResearchDirection:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ResearchDirection) -> None:
        await self.session.delete(entity)
        await self.session.flush()
