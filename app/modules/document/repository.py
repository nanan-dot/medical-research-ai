"""document — 数据库访问"""

from __future__ import annotations

import builtins

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.document.model import Document


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
    ) -> list[Document]:
        statement = select(Document).order_by(Document.id).options(selectinload(Document.asset))
        if parse_status is not None:
            statement = statement.where(Document.parse_status == parse_status)
        if index_status is not None:
            statement = statement.where(Document.index_status == index_status)
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self, parse_status: str | None = None, index_status: str | None = None
    ) -> int:
        statement = select(func.count()).select_from(Document)
        if parse_status is not None:
            statement = statement.where(Document.parse_status == parse_status)
        if index_status is not None:
            statement = statement.where(Document.index_status == index_status)
        result = await self.session.execute(statement)
        return result.scalar_one()

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
