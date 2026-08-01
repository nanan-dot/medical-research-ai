"""model_config — 数据库访问"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.model_config.model import ModelConfig


class ModelConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> ModelConfig | None:
        result = await self.session.execute(
            select(ModelConfig).where(ModelConfig.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[ModelConfig]:
        result = await self.session.execute(
            select(ModelConfig).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: ModelConfig) -> ModelConfig:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelConfig) -> None:
        await self.session.delete(entity)
        await self.session.flush()
