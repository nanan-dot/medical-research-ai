from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.literature_search.history_strategy_model import (
    LiteratureSearchExecution,
    LiteratureSearchStrategy,
    LiteratureSearchStrategyVersion,
)


class StrategyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, strategy_id: int) -> LiteratureSearchStrategy | None:
        return await self.session.get(LiteratureSearchStrategy, strategy_id)

    async def versions(self, strategy_id: int) -> list[LiteratureSearchStrategyVersion]:
        result = await self.session.execute(
            select(LiteratureSearchStrategyVersion)
            .where(LiteratureSearchStrategyVersion.strategy_id == strategy_id)
            .order_by(LiteratureSearchStrategyVersion.version)
        )
        return list(result.scalars())

    async def get_version(
        self, strategy_id: int, version_number: int
    ) -> LiteratureSearchStrategyVersion | None:
        result = await self.session.execute(
            select(LiteratureSearchStrategyVersion).where(
                LiteratureSearchStrategyVersion.strategy_id == strategy_id,
                LiteratureSearchStrategyVersion.version == version_number,
            )
        )
        return result.scalar_one_or_none()

    async def executions(
        self, version_ids: list[int]
    ) -> list[LiteratureSearchExecution]:
        if not version_ids:
            return []
        result = await self.session.execute(
            select(LiteratureSearchExecution)
            .where(LiteratureSearchExecution.strategy_version_id.in_(version_ids))
            .order_by(
                LiteratureSearchExecution.created_at.desc(),
                LiteratureSearchExecution.id.desc(),
            )
        )
        return list(result.scalars())

    async def related_records(
        self, strategy_ids: list[int]
    ) -> tuple[
        dict[int, list[LiteratureSearchStrategyVersion]],
        dict[int, list[LiteratureSearchExecution]],
    ]:
        """批量读取策略版本和执行记录，供列表与导出避免逐项查询。"""
        if not strategy_ids:
            return {}, {}
        versions_result = await self.session.execute(
            select(LiteratureSearchStrategyVersion)
            .where(LiteratureSearchStrategyVersion.strategy_id.in_(strategy_ids))
            .order_by(
                LiteratureSearchStrategyVersion.strategy_id,
                LiteratureSearchStrategyVersion.version,
            )
        )
        versions = list(versions_result.scalars())
        version_ids = [version.id for version in versions]
        executions_result = await self.session.execute(
            select(LiteratureSearchExecution)
            .where(LiteratureSearchExecution.strategy_version_id.in_(version_ids))
            .order_by(
                LiteratureSearchExecution.created_at.desc(),
                LiteratureSearchExecution.id.desc(),
            )
        )
        versions_by_strategy: dict[int, list[LiteratureSearchStrategyVersion]] = (
            defaultdict(list)
        )
        for version in versions:
            versions_by_strategy[version.strategy_id].append(version)
        executions_by_version: dict[int, list[LiteratureSearchExecution]] = defaultdict(
            list
        )
        for execution in executions_result.scalars():
            executions_by_version[execution.strategy_version_id].append(execution)
        return dict(versions_by_strategy), dict(executions_by_version)

    async def list(
        self,
        *,
        query: str | None,
        archived: bool,
        research_context_id: int | None,
        framework: str | None,
        created_from: datetime | None,
        has_changes: bool | None,
        execution_status: str | None,
        sort: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LiteratureSearchStrategy], int]:
        statement = select(LiteratureSearchStrategy).where(
            LiteratureSearchStrategy.is_archived == archived
        )
        if query:
            matching_versions = select(
                LiteratureSearchStrategyVersion.strategy_id
            ).where(
                or_(
                    LiteratureSearchStrategyVersion.original_query.contains(query),
                    LiteratureSearchStrategyVersion.search_string.contains(query),
                    LiteratureSearchStrategyVersion.term_groups_json.contains(query),
                    LiteratureSearchStrategyVersion.mesh_terms_json.contains(query),
                )
            )
            statement = statement.where(
                or_(
                    LiteratureSearchStrategy.name.contains(query),
                    LiteratureSearchStrategy.id.in_(matching_versions),
                )
            )
        if research_context_id is not None:
            statement = statement.where(
                LiteratureSearchStrategy.research_context_id == research_context_id
            )
        if framework:
            statement = statement.where(LiteratureSearchStrategy.framework == framework)
        if created_from:
            statement = statement.where(
                LiteratureSearchStrategy.created_at >= created_from
            )
        latest_execution_id = (
            select(LiteratureSearchExecution.id)
            .join(
                LiteratureSearchStrategyVersion,
                LiteratureSearchExecution.strategy_version_id
                == LiteratureSearchStrategyVersion.id,
            )
            .where(LiteratureSearchStrategyVersion.strategy_id == LiteratureSearchStrategy.id)
            .order_by(LiteratureSearchExecution.created_at.desc(), LiteratureSearchExecution.id.desc())
            .limit(1)
            .correlate(LiteratureSearchStrategy)
            .scalar_subquery()
        )
        if has_changes is not None:
            statement = statement.where(
                select(LiteratureSearchExecution.has_changes)
                .where(LiteratureSearchExecution.id == latest_execution_id)
                .scalar_subquery()
                == has_changes
            )
        if execution_status:
            statement = statement.where(
                select(LiteratureSearchExecution.status)
                .where(LiteratureSearchExecution.id == latest_execution_id)
                .scalar_subquery()
                == execution_status
            )

        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(statement.subquery())
                )
            ).scalar_one()
        )
        ordering = {
            "name": (LiteratureSearchStrategy.name.asc(),),
            "created_at": (LiteratureSearchStrategy.created_at.desc(),),
            "updated_at": (LiteratureSearchStrategy.updated_at.desc(),),
        }.get(
            sort,
            (
                LiteratureSearchStrategy.is_pinned.desc(),
                LiteratureSearchStrategy.updated_at.desc(),
            ),
        )
        result = await self.session.execute(
            statement.order_by(*ordering).offset(offset).limit(limit)
        )
        return list(result.scalars()), total

    async def add(self, entity):
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
