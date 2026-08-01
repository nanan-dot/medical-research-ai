"""evaluation — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.evaluation.model import Evaluation


class EvaluationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Evaluation | None:
        result = await self.session.execute(
            select(Evaluation).where(Evaluation.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[Evaluation]:
        result = await self.session.execute(
            select(Evaluation).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: Evaluation) -> Evaluation:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Evaluation) -> None:
        await self.session.delete(entity)
        await self.session.flush()
