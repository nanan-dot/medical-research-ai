"""knowledge_source — 数据库访问"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_source.model import KnowledgeSource


class KnowledgeSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[KnowledgeSource]:
        result = await self.session.execute(
            select(KnowledgeSource)
            .order_by(KnowledgeSource.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_normalized_path(self, path: str) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.normalized_root_path == path)
        )
        return result.scalar_one_or_none()

    async def create(self, entity: KnowledgeSource) -> KnowledgeSource:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: KnowledgeSource) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self, entity: KnowledgeSource) -> KnowledgeSource:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
