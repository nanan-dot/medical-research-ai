"""候选研究方向的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research_direction.model import ResearchDirection


class ResearchDirectionRepository:
    """只负责候选方向实体的持久化，不调用模型。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(
        self, entities: list[ResearchDirection]
    ) -> list[ResearchDirection]:
        self._session.add_all(entities)
        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)
        return entities

    async def get(self, direction_id: int) -> ResearchDirection | None:
        return await self._session.get(ResearchDirection, direction_id)

    async def list_for_matrix(self, matrix_id: int) -> list[ResearchDirection]:
        result = await self._session.execute(
            select(ResearchDirection).where(
                ResearchDirection.evidence_matrix_id == matrix_id
            )
        )
        return list(result.scalars())

    async def list_by_ids(self, direction_ids: list[int]) -> list[ResearchDirection]:
        result = await self._session.execute(
            select(ResearchDirection).where(ResearchDirection.id.in_(direction_ids))
        )
        return list(result.scalars())

    async def save(self, entity: ResearchDirection) -> ResearchDirection:
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: ResearchDirection) -> None:
        await self._session.delete(entity)
        await self._session.flush()
