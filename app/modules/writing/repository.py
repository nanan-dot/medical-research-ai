"""writing — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.writing.model import Writing


class WritingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Writing | None:
        result = await self.session.execute(select(Writing).where(Writing.id == id))
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[Writing]:
        result = await self.session.execute(select(Writing).offset(offset).limit(limit))
        return list(result.scalars().all())

    async def create(self, entity: Writing) -> Writing:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Writing) -> None:
        await self.session.delete(entity)
        await self.session.flush()
