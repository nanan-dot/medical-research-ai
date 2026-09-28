"""knowledge_source — 数据库访问"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, case, delete, exists, func, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.knowledge_source.auto_sync_policy import next_auto_sync_at
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.research_context.model import (
    KnowledgeSourceResearchContext,
    ResearchContext,
)

PARSE_STATUS_SUCCEEDED = "succeeded"
PARSE_STATUS_PENDING = "pending"
PARSE_STATUS_PARSING = "parsing"
PARSE_STATUS_FAILED = "failed"
INDEX_STATUS_SUCCEEDED = "succeeded"
INDEX_STATUS_FAILED = "failed"
INDEX_STATUS_OUTDATED = "outdated"
INDEX_STATUS_INDEXING = "indexing"


@dataclass(frozen=True)
class KnowledgeSourceStatsRecord:
    """聚合查询返回的知识源文档统计。"""

    total_files: int
    parsed: int
    indexed: int
    pending: int
    failed: int
    available: int
    processing: int
    needs_attention: int


class KnowledgeSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == id)
        )
        return result.scalar_one_or_none()

    async def mark_opened(self, id: int, actor_id: str | None = None) -> None:
        """Record a real document/source access without inferring a user identity."""
        entity = await self.get(id)
        if entity is None:
            return
        entity.last_opened_at = datetime.now(UTC)
        entity.last_opened_by = actor_id
        await self.session.flush()

    async def due_auto_sync_ids(self, now: datetime) -> builtins.list[int]:
        """返回候选 ID；并发声明由 claim_auto_sync 的条件更新负责。"""
        result = await self.session.execute(
            select(KnowledgeSource.id)
            .where(
                KnowledgeSource.auto_sync.is_(True),
                KnowledgeSource.enabled.is_(True),
                KnowledgeSource.sync_status.not_in(("unavailable", "scanning")),
                KnowledgeSource.next_auto_sync_at.is_not(None),
                KnowledgeSource.next_auto_sync_at <= now,
            )
            .order_by(KnowledgeSource.next_auto_sync_at, KnowledgeSource.id)
        )
        return list(result.scalars())

    async def claim_auto_sync(
        self, source_id: int, now: datetime
    ) -> KnowledgeSource | None:
        """通过条件 UPDATE 适配 SQLite，不依赖 SKIP LOCKED。"""
        source = await self.get(source_id)
        if source is None:
            return None
        result = await self.session.execute(
            update(KnowledgeSource)
            .where(
                KnowledgeSource.id == source_id,
                KnowledgeSource.auto_sync.is_(True),
                KnowledgeSource.enabled.is_(True),
                KnowledgeSource.sync_status.not_in(("unavailable", "scanning")),
                KnowledgeSource.next_auto_sync_at.is_not(None),
                KnowledgeSource.next_auto_sync_at <= now,
            )
            .values(
                last_auto_sync_enqueued_at=now,
                next_auto_sync_at=next_auto_sync_at(now, source.sync_interval_minutes),
            )
        )
        if getattr(result, "rowcount", 0) != 1:
            return None
        await self.session.refresh(source)
        return source

    async def record_auto_sync_enqueue_failure(
        self, source: KnowledgeSource, now: datetime
    ) -> None:
        """投递失败也必须留下可恢复的退避计划，防止来源静默漏同步。"""
        source.auto_sync_failure_count += 1
        source.next_auto_sync_at = next_auto_sync_at(
            now, source.sync_interval_minutes, source.auto_sync_failure_count
        )
        await self.session.flush()

    async def list(
        self, offset: int = 0, limit: int = 20
    ) -> builtins.list[KnowledgeSource]:
        result = await self.session.execute(
            select(KnowledgeSource)
            .order_by(KnowledgeSource.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def page(
        self,
        q: str | None,
        source_type: str | None,
        health_status: str | None,
        enabled: bool | None,
        auto_sync: bool | None,
        is_pinned: bool | None,
        research_context_id: int | None,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> tuple[builtins.list[KnowledgeSource], int]:
        statement = select(KnowledgeSource)
        if q:
            pattern = f"%{self._escape_like(q.casefold())}%"
            statement = statement.where(
                or_(
                    func.lower(KnowledgeSource.name).like(pattern, escape="\\"),
                    func.lower(KnowledgeSource.root_path).like(pattern, escape="\\"),
                    exists(
                        select(KnowledgeSourceResearchContext.id)
                        .join(
                            ResearchContext,
                            ResearchContext.id
                            == KnowledgeSourceResearchContext.research_context_id,
                        )
                        .where(
                            KnowledgeSourceResearchContext.knowledge_source_id
                            == KnowledgeSource.id,
                            func.lower(ResearchContext.name).like(
                                pattern, escape="\\"
                            ),
                        )
                    ),
                )
            )
        if research_context_id is not None:
            statement = statement.where(
                exists(
                    select(KnowledgeSourceResearchContext.id).where(
                        KnowledgeSourceResearchContext.knowledge_source_id
                        == KnowledgeSource.id,
                        KnowledgeSourceResearchContext.research_context_id
                        == research_context_id,
                    )
                )
            )
        for column, value in (
            (KnowledgeSource.source_type, source_type),
            (KnowledgeSource.enabled, enabled),
            (KnowledgeSource.auto_sync, auto_sync),
            (KnowledgeSource.is_pinned, is_pinned),
        ):
            if value is not None:
                statement = statement.where(column == value)
        if health_status is not None:
            has_problem = exists(
                select(Document.id).where(
                    Document.knowledge_source_id == KnowledgeSource.id,
                    or_(
                        Document.parse_status == PARSE_STATUS_FAILED,
                        Document.index_status.in_(
                            (INDEX_STATUS_FAILED, INDEX_STATUS_OUTDATED)
                        ),
                    ),
                )
            )
            if health_status == "paused":
                statement = statement.where(KnowledgeSource.enabled.is_(False))
            elif health_status == "unavailable":
                statement = statement.where(
                    KnowledgeSource.enabled.is_(True),
                    KnowledgeSource.sync_status == "unavailable",
                )
            elif health_status == "syncing":
                statement = statement.where(
                    KnowledgeSource.enabled.is_(True),
                    KnowledgeSource.sync_status == "scanning",
                )
            elif health_status == "needs_attention":
                statement = statement.where(
                    KnowledgeSource.enabled.is_(True),
                    KnowledgeSource.sync_status.not_in(("unavailable", "scanning")),
                    or_(
                        KnowledgeSource.sync_status == "completed_with_errors",
                        has_problem,
                    ),
                )
            else:
                statement = statement.where(
                    KnowledgeSource.enabled.is_(True),
                    KnowledgeSource.sync_status.not_in(
                        ("unavailable", "scanning", "completed_with_errors")
                    ),
                    not_(has_problem),
                )
        count_statement = statement.with_only_columns(
            func.count(KnowledgeSource.id)
        ).order_by(None)
        total = int((await self.session.execute(count_statement)).scalar_one())
        descending = sort_order == "desc"
        if sort_by == "name":
            order_column = func.lower(KnowledgeSource.name)
            statement = statement.order_by(
                order_column.desc() if descending else order_column.asc(),
                KnowledgeSource.id,
            )
        elif sort_by == "last_sync":
            statement = statement.order_by(
                KnowledgeSource.last_sync_time.is_(None),
                KnowledgeSource.last_sync_time.desc()
                if descending
                else KnowledgeSource.last_sync_time.asc(),
                KnowledgeSource.id,
            )
        elif sort_by == "last_opened":
            # 最近使用只反映用户显式访问；将 NULL 固定排末尾，避免不同数据库
            # 对空值排序的默认差异破坏分页稳定性。
            statement = statement.order_by(
                KnowledgeSource.is_pinned.desc(),
                KnowledgeSource.last_opened_at.is_(None),
                KnowledgeSource.last_opened_at.desc()
                if descending
                else KnowledgeSource.last_opened_at.asc(),
                KnowledgeSource.id.asc(),
            )
        else:
            statement = statement.order_by(
                KnowledgeSource.is_pinned.desc(),
                KnowledgeSource.last_sync_time.is_(None),
                KnowledgeSource.last_sync_time.desc(),
                KnowledgeSource.id,
            )
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def research_contexts_by_source_ids(
        self, source_ids: builtins.list[int]
    ) -> dict[int, builtins.list[tuple[int, str]]]:
        """批量读取来源关联，避免列表序列化形成 N+1 查询。"""
        if not source_ids:
            return {}
        result = await self.session.execute(
            select(
                KnowledgeSourceResearchContext.knowledge_source_id,
                ResearchContext.id,
                ResearchContext.name,
            )
            .join(
                ResearchContext,
                ResearchContext.id
                == KnowledgeSourceResearchContext.research_context_id,
            )
            .where(KnowledgeSourceResearchContext.knowledge_source_id.in_(source_ids))
            .order_by(
                KnowledgeSourceResearchContext.knowledge_source_id,
                func.lower(ResearchContext.name),
                ResearchContext.id,
            )
        )
        contexts: dict[int, builtins.list[tuple[int, str]]] = {}
        for source_id, context_id, name in result:
            contexts.setdefault(source_id, []).append((context_id, name))
        return contexts

    async def research_context_link(
        self, source_id: int, context_id: int
    ) -> KnowledgeSourceResearchContext | None:
        result = await self.session.execute(
            select(KnowledgeSourceResearchContext).where(
                KnowledgeSourceResearchContext.knowledge_source_id == source_id,
                KnowledgeSourceResearchContext.research_context_id == context_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_research_context_link(
        self, source_id: int, context_id: int
    ) -> None:
        self.session.add(
            KnowledgeSourceResearchContext(
                knowledge_source_id=source_id,
                research_context_id=context_id,
            )
        )
        await self.session.flush()

    async def remove_research_context_link(
        self, source_id: int, context_id: int
    ) -> bool:
        result = await self.session.execute(
            delete(KnowledgeSourceResearchContext).where(
                KnowledgeSourceResearchContext.knowledge_source_id == source_id,
                KnowledgeSourceResearchContext.research_context_id == context_id,
            )
        )
        return bool(getattr(result, "rowcount", 0))

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async def get_by_normalized_path(self, path: str) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.normalized_root_path == path)
        )
        return result.scalar_one_or_none()

    async def summary(self) -> dict[str, int]:
        """Aggregate supported knowledge sources and their documents in SQL."""
        supported = ("local_folder", "obsidian_vault")
        is_unavailable_file = or_(
            KnowledgeSource.sync_status == "unavailable",
            Document.error_code == "source_file_missing",
        )
        is_not_unavailable_file = and_(
            KnowledgeSource.sync_status != "unavailable",
            or_(
                Document.error_code.is_(None),
                Document.error_code != "source_file_missing",
            ),
        )
        is_unsupported = and_(
            is_not_unavailable_file,
            Document.error_code == "unsupported_document_type",
        )
        is_not_unsupported = or_(
            Document.error_code.is_(None),
            Document.error_code != "unsupported_document_type",
        )
        is_parse_failed = and_(
            is_not_unavailable_file,
            is_not_unsupported,
            Document.parse_status == PARSE_STATUS_FAILED,
        )
        is_index_failed = and_(
            is_not_unavailable_file,
            is_not_unsupported,
            Document.parse_status != PARSE_STATUS_FAILED,
            Document.index_status.in_((INDEX_STATUS_FAILED, INDEX_STATUS_OUTDATED)),
        )
        issue = or_(
            Document.parse_status == PARSE_STATUS_FAILED,
            Document.index_status.in_((INDEX_STATUS_FAILED, INDEX_STATUS_OUTDATED)),
            Document.error_code == "source_file_missing",
            KnowledgeSource.sync_status == "unavailable",
        )
        result = await self.session.execute(
            select(
                func.count(func.distinct(KnowledgeSource.id)).label("source_count"),
                func.count(
                    func.distinct(
                        case(
                            (
                                KnowledgeSource.source_type == "local_folder",
                                KnowledgeSource.id,
                            )
                        )
                    )
                ).label("local_folder_count"),
                func.count(
                    func.distinct(
                        case(
                            (
                                KnowledgeSource.source_type == "obsidian_vault",
                                KnowledgeSource.id,
                            )
                        )
                    )
                ).label("obsidian_count"),
                func.count(Document.id).label("total_item_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Document.parse_status == PARSE_STATUS_SUCCEEDED,
                                    Document.index_status == INDEX_STATUS_SUCCEEDED,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("available_item_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    or_(
                                        Document.parse_status.in_(
                                            (PARSE_STATUS_PENDING, PARSE_STATUS_PARSING)
                                        ),
                                        Document.index_status == INDEX_STATUS_INDEXING,
                                    ),
                                    ~issue,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("processing_item_count"),
                func.coalesce(func.sum(case((issue, 1), else_=0)), 0).label(
                    "needs_attention_count"
                ),
                func.count(func.distinct(case((issue, KnowledgeSource.id)))).label(
                    "affected_source_count"
                ),
                func.coalesce(
                    func.sum(case((is_parse_failed, 1), else_=0)), 0
                ).label("parse_failed"),
                func.coalesce(
                    func.sum(case((is_unsupported, 1), else_=0)), 0
                ).label("unsupported_format"),
                func.coalesce(
                    func.sum(case((is_unavailable_file, 1), else_=0)), 0
                ).label("unavailable_file"),
                func.coalesce(
                    func.sum(case((is_index_failed, 1), else_=0)), 0
                ).label("index_failed"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    issue,
                                    is_not_unavailable_file,
                                    is_not_unsupported,
                                    Document.parse_status != PARSE_STATUS_FAILED,
                                    Document.index_status.not_in(
                                        (INDEX_STATUS_FAILED, INDEX_STATUS_OUTDATED)
                                    ),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("other"),
            )
            .select_from(KnowledgeSource)
            .outerjoin(Document)
            .where(KnowledgeSource.source_type.in_(supported))
        )
        return {
            name: int(value or 0) for name, value in result.mappings().one().items()
        }

    async def stats_by_source_ids(
        self, source_ids: builtins.list[int]
    ) -> dict[int, KnowledgeSourceStatsRecord]:
        if not source_ids:
            return {}
        result = await self.session.execute(
            select(
                Document.knowledge_source_id,
                func.count(Document.id).label("total_files"),
                func.coalesce(
                    func.sum(
                        case(
                            (Document.parse_status == PARSE_STATUS_SUCCEEDED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("parsed"),
                func.coalesce(
                    func.sum(
                        case(
                            (Document.index_status == INDEX_STATUS_SUCCEEDED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("indexed"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Document.parse_status.in_(
                                    (PARSE_STATUS_PENDING, PARSE_STATUS_PARSING)
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("pending"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (
                                    (Document.parse_status == PARSE_STATUS_FAILED)
                                    | (Document.index_status == INDEX_STATUS_FAILED)
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("failed"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Document.parse_status == PARSE_STATUS_SUCCEEDED,
                                    Document.index_status == INDEX_STATUS_SUCCEEDED,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("available"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    or_(
                                        Document.parse_status.in_(
                                            (PARSE_STATUS_PENDING, PARSE_STATUS_PARSING)
                                        ),
                                        Document.index_status == INDEX_STATUS_INDEXING,
                                    ),
                                    Document.parse_status != PARSE_STATUS_FAILED,
                                    Document.index_status != INDEX_STATUS_FAILED,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("processing"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                or_(
                                    Document.parse_status == PARSE_STATUS_FAILED,
                                    Document.index_status.in_(
                                        (INDEX_STATUS_FAILED, INDEX_STATUS_OUTDATED)
                                    ),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("needs_attention"),
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
                available=row.available,
                processing=row.processing,
                needs_attention=row.needs_attention,
            )
            for row in result
        }

    async def create(self, entity: KnowledgeSource) -> KnowledgeSource:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: KnowledgeSource) -> None:
        # 显式子记录删除保证测试引擎或旧 SQLite 连接未启用 FK 时语义仍一致。
        await self.session.execute(
            delete(Document).where(Document.knowledge_source_id == entity.id)
        )
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self, entity: KnowledgeSource) -> KnowledgeSource:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
