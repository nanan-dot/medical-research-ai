"""Async database access for evidence-matrix entities only."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evidence_matrix.model import (
    EvidenceMatrix,
    MatrixCell,
    MatrixDocument,
    MatrixField,
)


class EvidenceMatrixRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: EvidenceMatrix) -> EvidenceMatrix:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_matrix(self, matrix_id: int) -> EvidenceMatrix | None:
        return await self.session.get(EvidenceMatrix, matrix_id)

    async def list_matrices(self, offset: int, limit: int) -> list[EvidenceMatrix]:
        """分页列出矩阵（按 id 倒序）。"""
        result = await self.session.execute(
            select(EvidenceMatrix).order_by(EvidenceMatrix.id.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars())

    async def count_matrices(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(EvidenceMatrix))
        return result.scalar_one()

    async def delete_matrix(self, entity: EvidenceMatrix) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def list_fields(self, matrix_id: int) -> list[MatrixField]:
        result = await self.session.execute(
            select(MatrixField)
            .where(MatrixField.matrix_id == matrix_id)
            .where(MatrixField.active.is_(True))  # 软删除的字段不返回
            .order_by(MatrixField.position)
        )
        return list(result.scalars())

    async def list_documents(self, matrix_id: int) -> list[MatrixDocument]:
        result = await self.session.execute(
            select(MatrixDocument).where(MatrixDocument.matrix_id == matrix_id)
        )
        return list(result.scalars())

    async def list_cells(self, matrix_id: int) -> list[MatrixCell]:
        result = await self.session.execute(
            select(MatrixCell).where(MatrixCell.matrix_id == matrix_id)
        )
        return list(result.scalars())

    async def get_document(self, matrix_id: int, document_id: int) -> MatrixDocument | None:
        result = await self.session.execute(
            select(MatrixDocument).where(
                MatrixDocument.matrix_id == matrix_id,
                MatrixDocument.document_id == document_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_field(self, matrix_id: int, field_key: str) -> MatrixField | None:
        result = await self.session.execute(
            select(MatrixField).where(
                MatrixField.matrix_id == matrix_id,
                MatrixField.field_key == field_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_cell(self, matrix_id: int, document_id: int, field_key: str) -> MatrixCell | None:
        result = await self.session.execute(
            select(MatrixCell).where(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.document_id == document_id,
                MatrixCell.field_key == field_key,
            )
        )
        return result.scalar_one_or_none()

    async def delete_cells_for_document(self, matrix_id: int, document_id: int) -> None:
        """移除文献时同步清理其单元格，避免 matrix_cells 残留孤儿数据。"""
        result = await self.session.execute(
            select(MatrixCell).where(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.document_id == document_id,
            )
        )
        for cell in result.scalars():
            await self.session.delete(cell)
        await self.session.flush()

    async def add_document(self, entity: MatrixDocument) -> MatrixDocument:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def add_field(self, entity: MatrixField) -> MatrixField:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def add_cells(self, entities: list[MatrixCell]) -> None:
        self.session.add_all(entities)
        await self.session.flush()

    async def delete_document(self, entity: MatrixDocument) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self) -> None:
        await self.session.flush()
