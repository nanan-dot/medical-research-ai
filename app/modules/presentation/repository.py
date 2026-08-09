from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.presentation.model import Presentation


class PresentationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, presentation_id: int) -> Presentation | None:
        return await self._session.get(Presentation, presentation_id)

    async def create(self, entity: Presentation) -> Presentation:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def save(self, entity: Presentation) -> Presentation:
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
