"""conversation — 业务逻辑"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.conversation.repository import ConversationRepository
from app.common.exceptions import NotFoundError


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.repo = ConversationRepository(session)

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"Conversation not found: {id}")
        return entity

    async def list(self, offset: int = 0, limit: int = 20):
        return await self.repo.list(offset=offset, limit=limit)

    async def delete(self, id: int):
        entity = await self.get(id)
        await self.repo.delete(entity)
        return entity
