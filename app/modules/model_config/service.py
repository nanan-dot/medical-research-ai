"""model_config — 业务逻辑"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.model_config.repository import ModelConfigRepository
from app.common.exceptions import NotFoundError


class ModelConfigService:
    def __init__(self, session: AsyncSession):
        self.repo = ModelConfigRepository(session)

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"ModelConfig not found: {id}")
        return entity

    async def list(self, offset: int = 0, limit: int = 20):
        return await self.repo.list(offset=offset, limit=limit)

    async def delete(self, id: int):
        entity = await self.get(id)
        await self.repo.delete(entity)
        return entity
