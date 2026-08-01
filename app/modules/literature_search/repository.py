"""literature_search — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.literature_search.model import LiteratureSearch


class LiteratureSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> LiteratureSearch | None:
        result = await self.session.execute(
            select(LiteratureSearch).where(LiteratureSearch.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[LiteratureSearch]:
        result = await self.session.execute(
            select(LiteratureSearch).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: LiteratureSearch) -> LiteratureSearch:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: LiteratureSearch) -> None:
        await self.session.delete(entity)
        await self.session.flush()
