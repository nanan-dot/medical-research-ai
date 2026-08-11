"""document — 数据库访问"""

from __future__ import annotations

import builtins

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.document.model import Document
from app.modules.document_upload.model import DocumentAsset

PARSE_STATUS_SUCCEEDED = "succeeded"
INDEX_STATUS_SUCCEEDED = "succeeded"
PDF_MEDIA_TYPES = frozenset({"application/pdf", "application/x-pdf"})


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Document | None:
        result = await self.session.execute(
            select(Document)
            .where(Document.id == id)
            .options(selectinload(Document.asset))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        parse_status: str | None = None,
        index_status: str | None = None,
        query: str | None = None,
        research_ready: bool = False,
        previewable_only: bool = False,
        knowledge_source_id: int | None = None,
    ) -> list[Document]:
        statement = self._filtered_statement(
            parse_status,
            index_status,
            query,
            research_ready,
            previewable_only,
            knowledge_source_id,
        ).order_by(Document.id).options(selectinload(Document.asset))
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self, parse_status: str | None = None, index_status: str | None = None,
        query: str | None = None, research_ready: bool = False,
        previewable_only: bool = False,
        knowledge_source_id: int | None = None,
    ) -> int:
        statement = self._filtered_statement(
            parse_status,
            index_status,
            query,
            research_ready,
            previewable_only,
            knowledge_source_id,
        ).with_only_columns(func.count()).order_by(None)
        result = await self.session.execute(statement)
        return result.scalar_one()

    @staticmethod
    def _filtered_statement(
        parse_status: str | None, index_status: str | None, query: str | None,
        research_ready: bool, previewable_only: bool,
        knowledge_source_id: int | None,
    ):
        statement = select(Document)
        if parse_status is not None:
            statement = statement.where(Document.parse_status == parse_status)
        if index_status is not None:
            statement = statement.where(Document.index_status == index_status)
        if knowledge_source_id is not None:
            statement = statement.where(
                Document.knowledge_source_id == knowledge_source_id
            )
        if query is not None or previewable_only:
            statement = statement.outerjoin(DocumentAsset)
        if query is not None:
            escaped_query = DocumentRepository._escape_like(query.casefold())
            pattern = f"%{escaped_query}%"
            statement = statement.where(
                or_(
                    func.lower(Document.file_path).like(pattern, escape="\\"),
                    func.lower(DocumentAsset.original_filename).like(pattern, escape="\\"),
                )
            )
        if research_ready:
            statement = statement.where(
                Document.parse_status == PARSE_STATUS_SUCCEEDED,
                Document.index_status == INDEX_STATUS_SUCCEEDED,
                Document.paperqa_index_key.is_not(None),
                Document.paperqa_index_key != "",
            )
        if previewable_only:
            # 上传模块只认可这两个 PDF MIME 类型；不按文件扩展名推断可预览性。
            statement = statement.where(
                DocumentAsset.media_type.in_(PDF_MEDIA_TYPES)
            )
        return statement

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async def list_by_source(self, knowledge_source_id: int) -> builtins.list[Document]:
        result = await self.session.execute(
            select(Document).where(Document.knowledge_source_id == knowledge_source_id)
        )
        return list(result.scalars().all())

    async def list_all(self) -> builtins.list[Document]:
        result = await self.session.execute(
            select(Document).order_by(Document.id).options(selectinload(Document.asset))
        )
        return list(result.scalars().all())

    async def create(self, entity: Document) -> Document:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Document) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self, entity: Document) -> Document:
        await self.session.flush()
        return entity
