from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.outline.model import Outline


class OutlineRepository:
    def __init__(self, session: AsyncSession):
        self.s = session

    async def get(self, id: int):
        return await self.s.get(Outline, id)

    async def create(self, e: Outline):
        self.s.add(e)
        await self.s.flush()
        await self.s.refresh(e)
        return e

    async def save(self, e: Outline):
        await self.s.flush()
        await self.s.refresh(e)
        return e
