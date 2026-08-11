"""knowledge_source — 数据库访问"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource

PARSE_STATUS_SUCCEEDED = "succeeded"
PARSE_STATUS_PENDING = "pending"
PARSE_STATUS_PARSING = "parsing"
PARSE_STATUS_FAILED = "failed"
INDEX_STATUS_SUCCEEDED = "succeeded"
INDEX_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class KnowledgeSourceStatsRecord:
    """聚合查询返回的知识源文档统计。"""

    total_files: int
    parsed: int
    indexed: int
    pending: int
    failed: int


class KnowledgeSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[KnowledgeSource]:
        result = await self.session.execute(
            select(KnowledgeSource)
            .order_by(KnowledgeSource.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_normalized_path(self, path: str) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.normalized_root_path == path)
        )
        return result.scalar_one_or_none()

    async def stats_by_source_ids(
        self, source_ids: list[int]
    ) -> dict[int, KnowledgeSourceStatsRecord]:
        if not source_ids:
            return {}
        result = await self.session.execute(
            select(
                Document.knowledge_source_id,
                func.count(Document.id).label("total_files"),
                func.coalesce(func.sum(case((Document.parse_status == PARSE_STATUS_SUCCEEDED, 1), else_=0)), 0).label("parsed"),
                func.coalesce(func.sum(case((Document.index_status == INDEX_STATUS_SUCCEEDED, 1), else_=0)), 0).label("indexed"),
                func.coalesce(func.sum(case((Document.parse_status.in_((PARSE_STATUS_PENDING, PARSE_STATUS_PARSING)), 1), else_=0)), 0).label("pending"),
                func.coalesce(func.sum(case((((Document.parse_status == PARSE_STATUS_FAILED) | (Document.index_status == INDEX_STATUS_FAILED)), 1), else_=0)), 0).label("failed"),
            )
            .where(Document.knowledge_source_id.in_(source_ids))
            .group_by(Document.knowledge_source_id)
        )
        return {
            row.knowledge_source_id: KnowledgeSourceStatsRecord(
                total_files=row.total_files,
                parsed=row.parsed,
                indexed=row.indexed,
                pending=row.pending,
                failed=row.failed,
            )
            for row in result
        }

    async def create(self, entity: KnowledgeSource) -> KnowledgeSource:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: KnowledgeSource) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self, entity: KnowledgeSource) -> KnowledgeSource:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
