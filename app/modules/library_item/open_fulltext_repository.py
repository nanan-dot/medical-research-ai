"""Database access for the ordered PMC acquisition audit trail."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library_item.open_fulltext_model import OpenFulltextAcquisition


class OpenFulltextAcquisitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_library_item(
        self, library_item_id: int
    ) -> OpenFulltextAcquisition | None:
        result = await self._session.execute(
            select(OpenFulltextAcquisition).where(
                OpenFulltextAcquisition.library_item_id == library_item_id
            ).order_by(OpenFulltextAcquisition.id.desc())
        )
        return result.scalars().first()

    async def list_by_library_item(
        self, library_item_id: int
    ) -> list[OpenFulltextAcquisition]:
        result = await self._session.execute(
            select(OpenFulltextAcquisition)
            .where(OpenFulltextAcquisition.library_item_id == library_item_id)
            .order_by(OpenFulltextAcquisition.id.desc())
        )
        return list(result.scalars().all())
