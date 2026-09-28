from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.model_config.model import ModelConfig


class ModelConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int):
        return await self.session.get(ModelConfig, id)

    async def list(self):
        result = await self.session.execute(
            select(ModelConfig).order_by(ModelConfig.id)
        )
        return list(result.scalars())

    async def default_local(self):
        result = await self.session.execute(
            select(ModelConfig).where(
                ModelConfig.is_default.is_(True),
                ModelConfig.provider == "ollama",
                ModelConfig.deployment_mode.in_(("local", "hybrid")),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, entity):
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def save(self, entity):
        await self.session.flush()
        return entity

    async def clear_defaults(self, except_id: int | None = None):
        statement = update(ModelConfig).values(is_default=False)
        if except_id is not None:
            statement = statement.where(ModelConfig.id != except_id)
        await self.session.execute(statement)

    async def delete(self, entity):
        await self.session.delete(entity)
        await self.session.flush()
