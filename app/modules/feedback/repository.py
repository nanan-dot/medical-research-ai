from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.feedback.model import Feedback


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int):
        return await self.session.get(Feedback, id)

    async def list(self):
        result = await self.session.execute(select(Feedback).order_by(Feedback.id))
        return list(result.scalars())

    async def create(self, entity):
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity):
        await self.session.delete(entity)
        await self.session.flush()
