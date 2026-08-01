"""evaluation — 业务逻辑"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.evaluation.repository import EvaluationRepository
from app.common.exceptions import NotFoundError


class EvaluationService:
    def __init__(self, session: AsyncSession):
        self.repo = EvaluationRepository(session)

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"Evaluation not found: {id}")
        return entity

    async def list(self, offset: int = 0, limit: int = 20):
        return await self.repo.list(offset=offset, limit=limit)

    async def delete(self, id: int):
        entity = await self.get(id)
        await self.repo.delete(entity)
        return entity
