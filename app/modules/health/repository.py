"""health — 数据库访问"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.health.model import Health


class HealthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Health | None:
        result = await self.session.execute(select(Health).where(Health.id == id))
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[Health]:
        result = await self.session.execute(select(Health).offset(offset).limit(limit))
        return list(result.scalars().all())

    async def create(self, entity: Health) -> Health:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Health) -> None:
        await self.session.delete(entity)
        await self.session.flush()
