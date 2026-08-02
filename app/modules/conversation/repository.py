from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.model import Citation, Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int):
        return await self.session.get(Conversation, id)

    async def create(self, entity):
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def save(self, entity):
        await self.session.flush()
        return entity

    async def messages(self, conversation_id: int):
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
        )
        return list(result.scalars())

    async def citations(self, message_id: int):
        result = await self.session.execute(
            select(Citation).where(Citation.message_id == message_id).order_by(Citation.id)
        )
        return list(result.scalars())

    async def next_sequence(self, conversation_id: int):
        value = await self.session.scalar(
            select(func.max(Message.sequence)).where(Message.conversation_id == conversation_id)
        )
        return int(value or 0) + 1
