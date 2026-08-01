"""conversation — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.conversation.model import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: Conversation) -> Conversation:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Conversation) -> None:
        await self.session.delete(entity)
        await self.session.flush()
