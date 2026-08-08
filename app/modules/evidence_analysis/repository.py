"""Read-only data access for evidence analysis."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evidence_matrix.model import EvidenceMatrix, MatrixCell, MatrixDocument
from app.modules.library_item.model import LibraryItem


class EvidenceAnalysisRepository:
    """Load one matrix and its local-library metadata in bounded queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_matrix(self, matrix_id: int) -> EvidenceMatrix | None:
        return await self._session.get(EvidenceMatrix, matrix_id)

    async def list_documents(self, matrix_id: int) -> list[MatrixDocument]:
        result = await self._session.execute(
            select(MatrixDocument).where(MatrixDocument.matrix_id == matrix_id)
        )
        return list(result.scalars())

    async def list_cells(self, matrix_id: int) -> list[MatrixCell]:
        result = await self._session.execute(select(MatrixCell).where(MatrixCell.matrix_id == matrix_id))
        return list(result.scalars())

    async def list_library_items_for_documents(self, document_ids: list[int]) -> list[LibraryItem]:
        if not document_ids:
            return []
        result = await self._session.execute(
            select(LibraryItem).where(LibraryItem.document_id.in_(document_ids))
        )
        return list(result.scalars())
