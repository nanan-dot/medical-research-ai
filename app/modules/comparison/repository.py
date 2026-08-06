"""Async database access for comparison entities only."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.comparison.model import ComparisonCell, ComparisonTask


class ComparisonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(self, entity: ComparisonTask) -> ComparisonTask:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_cells(self, cells: list[ComparisonCell]) -> None:
        self.session.add_all(cells)
        await self.session.flush()

    async def get_task(self, task_id: int) -> ComparisonTask | None:
        return await self.session.get(ComparisonTask, task_id)

    async def cells_for_task(self, task_id: int) -> list[ComparisonCell]:
        result = await self.session.execute(
            select(ComparisonCell).where(ComparisonCell.comparison_id == task_id)
        )
        return list(result.scalars())

    async def cell(self, task_id: int, document_id: int, field: str) -> ComparisonCell | None:
        result = await self.session.execute(
            select(ComparisonCell).where(
                ComparisonCell.comparison_id == task_id,
                ComparisonCell.document_id == document_id,
                ComparisonCell.field == field,
            )
        )
        return result.scalar_one_or_none()

    async def save(self) -> None:
        await self.session.flush()
