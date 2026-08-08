"""Database access for topic-structuring snapshots only."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.topic_structuring.model import TopicStructuring, TopicStructuringVersion


class TopicStructuringRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, entity: TopicStructuring) -> TopicStructuring:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def get(self, structuring_id: int) -> TopicStructuring | None:
        return await self._session.get(TopicStructuring, structuring_id)

    async def create_version(self, entity: TopicStructuringVersion) -> TopicStructuringVersion:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def get_version(self, structuring_id: int, version: int) -> TopicStructuringVersion | None:
        result = await self._session.execute(
            select(TopicStructuringVersion).where(
                TopicStructuringVersion.topic_structuring_id == structuring_id,
                TopicStructuringVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(self, structuring_id: int) -> list[TopicStructuringVersion]:
        result = await self._session.execute(
            select(TopicStructuringVersion)
            .where(TopicStructuringVersion.topic_structuring_id == structuring_id)
            .order_by(TopicStructuringVersion.version)
        )
        return list(result.scalars())

    async def save(self, entity: TopicStructuring) -> TopicStructuring:
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
