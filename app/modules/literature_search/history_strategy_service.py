import json
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.literature_search.history_strategy_diff import build_strategy_diff
from app.modules.literature_search.history_strategy_model import (
    LiteratureSearchExecution,
    LiteratureSearchStrategy,
    LiteratureSearchStrategyVersion,
)
from app.modules.literature_search.history_strategy_repository import StrategyRepository
from app.modules.literature_search.history_strategy_schema import *
from app.modules.literature_search.schema import SearchExecuteRequest
from app.modules.literature_search.service import LiteratureSearchService


class StrategyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StrategyRepository(session)

    def _version(self, v: LiteratureSearchStrategyVersion) -> StrategyVersionRead:
        return StrategyVersionRead(
            id=v.id,
            version=v.version,
            original_query=v.original_query,
            search_string=v.search_string,
            filters=v.filters,
            model_version=v.model_version,
            term_groups=json.loads(v.term_groups_json),
            mesh_terms=json.loads(v.mesh_terms_json),
            start_year=v.start_year,
            end_year=v.end_year,
            change_summary=json.loads(v.change_summary_json),
            created_at=v.created_at,
        )

    def _execution(
        self, e: LiteratureSearchExecution, versions: dict[int, int]
    ) -> ExecutionRead:
        return ExecutionRead(
            id=e.id,
            strategy_version_id=e.strategy_version_id,
            version=versions[e.strategy_version_id],
            result_id=e.result_id,
            status=e.status,
            result_count=e.result_count,
            error_message=e.error_message,
            created_at=e.created_at,
            completed_at=e.completed_at,
            requested_retmax=e.requested_retmax,
            previous_result_id=e.previous_result_id,
            added_count=e.added_count,
            removed_count=e.removed_count,
            added_pmids=json.loads(e.added_pmids_json) if e.added_pmids_json else None,
            removed_pmids=json.loads(e.removed_pmids_json) if e.removed_pmids_json else None,
            has_changes=e.has_changes,
        )

    def _detail_from_records(
        self,
        strategy: LiteratureSearchStrategy,
        versions: list[LiteratureSearchStrategyVersion],
        executions: list[LiteratureSearchExecution],
    ) -> StrategyRead:
        if not versions:
            raise NotFoundError(
                f"LiteratureSearchStrategy has no versions: {strategy.id}"
            )
        version_numbers = {version.id: version.version for version in versions}
        return StrategyRead(
            id=strategy.id,
            name=strategy.name,
            research_context_id=strategy.research_context_id,
            framework=strategy.framework,
            database=strategy.database,
            is_pinned=strategy.is_pinned,
            is_archived=strategy.is_archived,
            current_version=self._version(versions[-1]),
            versions=[self._version(version) for version in versions],
            executions=[
                self._execution(execution, version_numbers) for execution in executions
            ],
            updated_at=strategy.updated_at,
        )

    @staticmethod
    def _sort_executions(
        executions: list[LiteratureSearchExecution],
    ) -> list[LiteratureSearchExecution]:
        return sorted(
            executions,
            key=lambda execution: (execution.created_at, execution.id),
            reverse=True,
        )

    async def _touch_strategy(self, strategy_id: int) -> None:
        strategy = await self.repo.get(strategy_id)
        if strategy is None:
            raise NotFoundError(f"LiteratureSearchStrategy not found: {strategy_id}")
        strategy.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def detail(self, id: int):
        strategy = await self.repo.get(id)
        if not strategy:
            raise NotFoundError(f"LiteratureSearchStrategy not found: {id}")
        versions = await self.repo.versions(id)
        executions = await self.repo.executions([v.id for v in versions])
        return self._detail_from_records(strategy, versions, executions)

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
        sort: StrategySort,
        offset: int,
        limit: int,
    ):
        rows, total = await self.repo.list(
            query=query,
            archived=archived,
            research_context_id=research_context_id,
            framework=framework,
            created_from=created_from,
            has_changes=has_changes,
            execution_status=execution_status,
            sort=sort,
            offset=offset,
            limit=limit,
        )
        versions_by_strategy, executions_by_version = await self.repo.related_records(
            [row.id for row in rows]
        )
        items: list[StrategyListItem] = []
        for row in rows:
            versions = versions_by_strategy.get(row.id, [])
            executions = self._sort_executions(
                [
                    execution
                    for version in versions
                    for execution in executions_by_version.get(version.id, [])
                ]
            )
            detail = self._detail_from_records(row, versions, executions)
            v = detail.current_version
            latest = detail.executions[0] if detail.executions else None
            items.append(
                StrategyListItem(
                    id=row.id,
                    name=row.name,
                    research_context_id=row.research_context_id,
                    framework=row.framework,
                    is_pinned=row.is_pinned,
                    is_archived=row.is_archived,
                    current_version=v.version,
                    original_query=v.original_query,
                    keyword_count=len(v.term_groups),
                    mesh_count=len(v.mesh_terms),
                    start_year=v.start_year,
                    end_year=v.end_year,
                    latest_execution=latest,
                )
            )
        return StrategyPage(total=total, offset=offset, limit=limit, items=items)

    async def export(self) -> StrategyExportRead:
        rows, total = await self.repo.list(
            query=None,
            archived=False,
            research_context_id=None,
            framework=None,
            created_from=None,
            has_changes=None,
            execution_status=None,
            sort="created_at",
            offset=0,
            limit=10_000,
        )
        versions_by_strategy, executions_by_version = await self.repo.related_records(
            [row.id for row in rows]
        )
        strategies = [
            self._detail_from_records(
                row,
                versions_by_strategy.get(row.id, []),
                self._sort_executions(
                    [
                        execution
                        for version in versions_by_strategy.get(row.id, [])
                        for execution in executions_by_version.get(version.id, [])
                    ]
                ),
            )
            for row in rows
        ]
        return StrategyExportRead(
            exported_at=datetime.now(UTC), total=total, strategies=strategies
        )

    async def execute_version(
        self,
        strategy_id: int,
        version_number: int,
        request: StrategyExecuteRequest,
    ) -> ExecutionRead:
        """执行不可变版本快照，并把每次运行作为独立审计记录保存。

        复用既有 PubMed 执行服务，避免历史页产生与检索中心不一致的第二套
        抓取、验证或结果落库流程。策略版本只保存输入，执行记录只引用结果快照。
        """
        version = await self.repo.get_version(strategy_id, version_number)
        if version is None:
            raise NotFoundError(
                f"LiteratureSearchStrategyVersion not found: {strategy_id}/v{version_number}"
            )

        execution = await self.repo.add(
            LiteratureSearchExecution(
                strategy_version_id=version.id,
                status="running",
                requested_retmax=request.retmax,
                result_count=0,
            )
        )
        try:
            result = await LiteratureSearchService(self.session).execute_search(
                SearchExecuteRequest(
                    boolean_query=version.search_string,
                    retmax=request.retmax,
                )
            )
        except PubMedError as exc:
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.completed_at = datetime.now(UTC)
            await self._touch_strategy(strategy_id)
            await self.session.flush()
            return self._execution(execution, {version.id: version.version})

        execution.status = "succeeded"
        execution.result_id = result.id
        execution.result_count = result.total_count
        strategy_versions = await self.repo.versions(strategy_id)
        strategy_executions = await self.repo.executions(
            [strategy_version.id for strategy_version in strategy_versions]
        )
        previous = next(
            (
                item
                for item in strategy_executions
                if item.id != execution.id and item.status == "succeeded" and item.result_id
            ),
            None,
        )
        if previous is not None:
            search_service = LiteratureSearchService(self.session)
            previous_result = await search_service.repo.get_result(previous.result_id)
            current_result = await search_service.repo.get_result(result.id)
            previous_pmids = search_service._pmids_from_result(previous_result)
            current_pmids = search_service._pmids_from_result(current_result)
            added_pmids = sorted(current_pmids - previous_pmids)
            removed_pmids = sorted(previous_pmids - current_pmids)
            execution.previous_result_id = previous.result_id
            execution.added_count = len(added_pmids)
            execution.removed_count = len(removed_pmids)
            execution.added_pmids_json = json.dumps(added_pmids)
            execution.removed_pmids_json = json.dumps(removed_pmids)
            execution.has_changes = bool(added_pmids or removed_pmids)
        execution.completed_at = datetime.now(UTC)
        await self._touch_strategy(strategy_id)
        await self.session.flush()
        return self._execution(execution, {version.id: version.version})

    async def create(self, request: StrategyCreate):
        strategy = await self.repo.add(
            LiteratureSearchStrategy(
                name=request.name,
                research_context_id=request.research_context_id,
                framework=request.framework,
                database="pubmed",
            )
        )
        await self.repo.add(
            LiteratureSearchStrategyVersion(
                strategy_id=strategy.id,
                version=1,
                original_query=request.original_query,
                structured_query=request.structured_query,
                search_string=request.search_string,
                filters=request.filters,
                model_version=request.model_version,
                user_edits=request.user_edits,
                term_groups_json=json.dumps(request.term_groups, ensure_ascii=False),
                mesh_terms_json=json.dumps(request.mesh_terms, ensure_ascii=False),
                start_year=request.start_year,
                end_year=request.end_year,
                change_summary_json="{}",
            )
        )
        return await self.detail(strategy.id)

    async def patch(self, id: int, request: StrategyPatch):
        strategy = await self.repo.get(id)
        if not strategy:
            raise NotFoundError(f"LiteratureSearchStrategy not found: {id}")
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(strategy, field, value)
        strategy.updated_at = datetime.now(UTC)
        await self.session.flush()
        return await self.detail(id)

    async def add_version(self, id: int, request: StrategyVersionCreate):
        detail = await self.detail(id)
        if detail.current_version.version != request.expected_current_version:
            raise ConflictError("检索策略已产生新版本，请刷新后重试")
        current = request.model_dump(exclude={"expected_current_version"})
        previous = detail.current_version.model_dump()
        version = LiteratureSearchStrategyVersion(
            strategy_id=id,
            version=request.expected_current_version + 1,
            original_query=request.original_query,
            structured_query=request.structured_query,
            search_string=request.search_string,
            filters=request.filters,
            model_version=request.model_version,
            user_edits=request.user_edits,
            term_groups_json=json.dumps(request.term_groups, ensure_ascii=False),
            mesh_terms_json=json.dumps(request.mesh_terms, ensure_ascii=False),
            start_year=request.start_year,
            end_year=request.end_year,
            change_summary_json=json.dumps(
                build_strategy_diff(previous, current), ensure_ascii=False
            ),
        )
        try:
            # 预读版本号只能优化普通冲突；唯一约束才是并发下的最终裁决。
            async with self.session.begin_nested():
                self.session.add(version)
                await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("检索策略已产生新版本，请刷新后重试") from exc
        await self._touch_strategy(id)
        return await self.detail(id)

    async def clone(self, id: int, name: str | None):
        source = await self.detail(id)
        v = source.current_version
        result = await self.create(
            StrategyCreate(
                name=name or f"{source.name} - 副本",
                research_context_id=source.research_context_id,
                framework=source.framework,
                original_query=v.original_query,
                search_string=v.search_string,
                filters=v.filters,
                model_version=v.model_version,
                term_groups=v.term_groups,
                mesh_terms=v.mesh_terms,
                start_year=v.start_year,
                end_year=v.end_year,
            )
        )
        target = await self.repo.get(result.id)
        target.copied_from_strategy_id = id
        await self.session.flush()
        return result

    async def archive(self, id: int, value: bool):
        strategy = await self.repo.get(id)
        if not strategy:
            raise NotFoundError(f"LiteratureSearchStrategy not found: {id}")
        strategy.is_archived = value
        strategy.archived_at = datetime.now(UTC) if value else None
        strategy.updated_at = datetime.now(UTC)
        await self.session.flush()
        return await self.detail(id)

    async def compare(self, id: int, a: int, b: int):
        detail = await self.detail(id)
        lookup = {v.version: v for v in detail.versions}
        if a not in lookup or b not in lookup:
            raise NotFoundError("Strategy version not found")
        return StrategyCompareRead(
            from_version=a,
            to_version=b,
            changes=build_strategy_diff(lookup[a].model_dump(), lookup[b].model_dump()),
        )
