"""研究条件快照的数据库访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research_conditions.model import ResearchConditions, ResearchConditionsVersion


class ResearchConditionsRepository:
    """封装条件实体与版本快照的持久化，不承担业务校验。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, entity: ResearchConditions) -> ResearchConditions:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def get(self, conditions_id: int) -> ResearchConditions | None:
        result = await self._session.execute(
            select(ResearchConditions).where(ResearchConditions.id == conditions_id)
        )
        return result.scalar_one_or_none()

    async def get_version(
        self, conditions_id: int, version: int
    ) -> ResearchConditionsVersion | None:
        result = await self._session.execute(
            select(ResearchConditionsVersion).where(
                ResearchConditionsVersion.conditions_id == conditions_id,
                ResearchConditionsVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def create_version(
        self, entity: ResearchConditionsVersion
    ) -> ResearchConditionsVersion:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def save(self, entity: ResearchConditions) -> ResearchConditions:
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
