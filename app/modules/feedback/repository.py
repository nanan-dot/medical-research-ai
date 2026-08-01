"""feedback — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.feedback.model import Feedback


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Feedback | None:
        result = await self.session.execute(
            select(Feedback).where(Feedback.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[Feedback]:
        result = await self.session.execute(
            select(Feedback).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: Feedback) -> Feedback:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Feedback) -> None:
        await self.session.delete(entity)
        await self.session.flush()
