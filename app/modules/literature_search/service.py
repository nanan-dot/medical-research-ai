"""Literature-search intent orchestration."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage
from app.integrations.ollama.client import OllamaClient
from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.library_item.schema import LibraryItemRead
from app.modules.literature_search import filtering, ranking
from app.modules.literature_search.bibtex import to_bibtex
from app.modules.literature_search.dedup import (
    DedupRecord,
    DuplicateCandidate,
    find_duplicate_candidates,
    select_canonical_record,
)
from app.modules.literature_search.mesh_client import MeshClient
from app.modules.literature_search.model import (
    LiteratureDuplicateGroup,
    LiteratureDuplicateGroupMember,
    LiteratureDuplicateResolution,
    LiteratureReadingOrder,
    LiteratureSearchItemState,
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.literature_search.pico_fallback import extract_curated_pico
from app.modules.literature_search.prompts import PROMPT_VERSION, build_candidate_prompt
from app.modules.literature_search.pubmed_executor import PubMedExecutor
from app.modules.literature_search.query_builder import build_boolean_query
from app.modules.literature_search.query_model import (
    SearchIntentCandidate,
    relative_year_range,
)
from app.modules.literature_search.reading_order import (
    ReadingContext,
    apply_manual_order,
    classify_reading_item,
    rank_reading_order,
)
from app.modules.literature_search.repository import LiteratureSearchRepository
from app.modules.literature_search.schema import (
    BooleanQueryResult,
    CitationItem,
    DeduplicationSummary,
    DuplicateGroupList,
    DuplicateGroupMemberRead,
    DuplicateGroupPage,
    DuplicateGroupRead,
    DuplicateResolutionRead,
    DuplicateResolveRequest,
    ExpandTermsResponse,
    ItemStateRead,
    ItemStateUpdate,
    LiteratureSearchHistoryEntry,
    LiteratureSearchHistoryList,
    LiteratureSearchResultPage,
    LiteratureSearchResultRead,
    LiteratureSearchTaskCreate,
    LiteratureSearchTaskCreateResult,
    LiteratureSearchTaskList,
    LiteratureSearchTaskRead,
    LiteratureSearchTaskRerun,
    LiteratureSearchTaskVersion,
    MeshCandidate,
    ParseQueryResponse,
    RankedCitationItem,
    ReadingOrderItem,
    ReadingOrderRead,
    ReadStatus,
    ResultDuplicateResolutionRead,
    ResultDuplicateResolutionRequest,
    ResultQueryParams,
    SearchExecuteRequest,
    SearchResultChange,
    SearchStrategyExport,
    SearchTaskStatus,
    SearchTermGroup,
)
from app.modules.literature_search.term_expansion import (
    expand_term,
    is_ascii_search_term,
)
from app.modules.literature_search.user_state import (
    DEFAULT_READ_STATUS,
    deserialize_tags,
    serialize_tags,
)

CandidateExtractor = Callable[[str], Awaitable[str]]

# 任务状态机取值：pending → running → succeeded / failed。
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

# 合法状态集合：与 schema.SearchTaskStatus（Literal）保持一致。
_VALID_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED}
)


def _coerce_status(value: str) -> SearchTaskStatus:
    """把数据库读取的 str 状态收敛为 SearchTaskStatus Literal。

    设计说明：DB 列声明为 str（SQLite 无枚举），但响应模型要求 Literal；
    运行时校验一次保证只有合法状态能进入响应层，杜绝脏数据外泄。
    """
    if value not in _VALID_STATUSES:
        raise ValueError(f"invalid task status: {value!r}")
    return value  # type: ignore[return-value]  # 已用集合校验收敛为合法 Literal


def _canonical_json(value: str) -> object | str:
    """Parse JSON snapshots before deterministic serialization."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _normalize_user_edit_value(value: object) -> object:
    """Normalize user-edit JSON while preserving meaningful search terms."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        normalized_items = [_normalize_user_edit_value(item) for item in value]
        non_empty_items = [item for item in normalized_items if item != ""]
        return sorted(
            non_empty_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, dict):
        return {
            key: _normalize_user_edit_value(item)
            for key, item in sorted(value.items())
        }
    return value


def normalize_user_edits(raw: str) -> str:
    """Return a stable JSON representation of user edits without format-only differences."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    normalized = _normalize_user_edit_value(parsed)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def strategy_fingerprint_from_snapshot(
    *, database: str, search_string: str, filters: str, retmax: int,
    user_edits: str, model_version: str, structured_query: str,
    original_query: str,
) -> str:
    """返回精确任务身份，供复用与跨任务去重边界使用。"""
    snapshot = {
        "database": database,
        "search_string": search_string,
        "filters": _canonical_json(filters),
        "retmax": retmax,
        "user_edits": normalize_user_edits(user_edits),
        "model_version": model_version,
        "structured_query": _canonical_json(structured_query),
        "original_query": original_query,
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def history_fingerprint_from_snapshot(
    *, database: str, search_string: str, filters: str
) -> str:
    """返回主历史 read-model 的 PubMed 条件身份。"""
    canonical = json.dumps(
        {
            "database": database,
            "search_string": search_string,
            "filters": _canonical_json(filters),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def strategy_fingerprint(request: LiteratureSearchTaskCreate) -> str:
    """Build an exact strategy fingerprint from a validated create request."""
    return strategy_fingerprint_from_snapshot(
        database=request.database, search_string=request.search_string,
        filters=request.filters, retmax=request.retmax, user_edits=request.user_edits,
        model_version=request.model_version, structured_query=request.structured_query,
        original_query=request.original_query,
    )


class LiteratureSearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        candidate_extractor: CandidateExtractor | None = None,
        mesh_client: MeshClient | None = None,
        pubmed_executor: PubMedExecutor | None = None,
    ):
        # 保存 session 供批量全文状态查询等跨仓储操作使用（如
        # generate_reading_order 里的 LibraryItemRepository）。
        self.session = session
        self.repo = LiteratureSearchRepository(session)
        self.candidate_extractor = (
            candidate_extractor or self._extract_with_configured_model
        )
        self.mesh_client = mesh_client or MeshClient()
        self.pubmed_executor = pubmed_executor or PubMedExecutor(
            PubMedClient.from_settings()
        )

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"LiteratureSearch not found: {id}")
        return entity

    async def list_records(self, offset: int = 0, limit: int = 20):
        return await self.repo.list_records(offset=offset, limit=limit)

    async def delete(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearch not found: {id}")
        await self.repo.delete(entity)
        return entity

    async def parse_query(self, raw_topic: str) -> ParseQueryResponse:
        normalized = " ".join(raw_topic.split())
        fallback = self._rule_candidate(normalized)
        try:
            raw_json = await self.candidate_extractor(
                build_candidate_prompt(normalized)
            )
            candidate = self._constrain_candidate(
                SearchIntentCandidate.model_validate_json(raw_json), normalized
            )
            candidate = self._fill_missing_pico_fields(candidate, fallback)
            source = "model_candidate"
        except (ValueError, json.JSONDecodeError):
            candidate = fallback
            source = "rule_fallback"
        return ParseQueryResponse(
            raw_topic=raw_topic,
            candidate=candidate,
            clarification_questions=self._clarification_questions(candidate),
            candidate_source=source,
            prompt_version=PROMPT_VERSION,
        )

    async def expand_terms(
        self, candidate: SearchIntentCandidate, user_edits: dict[str, list[str]]
    ) -> ExpandTermsResponse:
        values = {
            "disease": candidate.disease,
            "intervention": candidate.intervention,
            "target": candidate.target,
            "mechanism": candidate.mechanism,
        }
        if not any(values.values()):
            values["topic"] = candidate.topic

        groups: list[SearchTermGroup] = []
        mesh_candidates: list[MeshCandidate] = []
        warnings: list[str] = []
        for name, value in values.items():
            if not value:
                continue
            expansion = expand_term(value)
            terms = list(
                dict.fromkeys([*expansion.synonyms, *user_edits.get(name, [])])
            )
            ascii_terms = [term for term in terms if is_ascii_search_term(term)]
            if len(ascii_terms) != len(terms):
                warnings.append(
                    f"{name}: Chinese-only terms were retained for editing but omitted from PubMed query output."
                )
            if not ascii_terms:
                continue
            groups.append(
                SearchTermGroup(
                    name=name,
                    core_term=expansion.core_term,
                    terms=ascii_terms,
                    source=expansion.source,
                )
            )
            try:
                rows = await self.mesh_client.lookup(expansion.core_term)
            except Exception:  # noqa: BLE001 — MeSH 查找失败降级：追加警告继续，不中断扩展流程。
                warnings.append(
                    f"{name}: official MeSH lookup was unavailable; no MeSH candidate was assumed."
                )
                continue
            mesh_candidates.extend(
                MeshCandidate(group_name=name, **row) for row in rows
            )
        return ExpandTermsResponse(
            term_groups=groups,
            mesh_candidates=mesh_candidates,
            warnings=warnings,
            user_edits=user_edits,
        )

    @staticmethod
    def build_query(groups: list[SearchTermGroup]) -> BooleanQueryResult:
        return build_boolean_query(groups)

    # ------------------------------------------------------------------
    # R2-WP04：检索任务与历史
    # ------------------------------------------------------------------

    async def create_task(
        self, request: LiteratureSearchTaskCreate
    ) -> LiteratureSearchTaskCreateResult:
        """创建检索任务并立即执行（pending → running → succeeded/failed）。

        设计说明：任务持久化的是完整检索输入快照，执行复用 WP03.5 的
        pubmed_executor（ESearch + EFetch + verified 打标），不新建平行执行逻辑。
        结果引用落到 LiteratureSearchResult，任务只保存结果 id，避免复制
        items_json 造成历史膨胀。
        """
        fingerprint = strategy_fingerprint(request)
        existing = await self.repo.get_task_by_fingerprint(fingerprint)
        if existing is None:
            existing = await self._find_legacy_task_by_fingerprint(fingerprint)
        if existing is not None:
            rerun = await self.rerun_task(existing.id)
            return LiteratureSearchTaskCreateResult(
                **rerun.task.model_dump(),
                operation="reused",
                change=rerun.change,
                new_result_id=rerun.new_result_id,
            )

        now = datetime.now(UTC)
        entity = LiteratureSearchTask(
            original_query=request.original_query,
            structured_query=request.structured_query,
            search_string=request.search_string,
            database=request.database,
            filters=request.filters,
            model_version=request.model_version,
            user_edits=request.user_edits,
            retmax=request.retmax,
            strategy_fingerprint=fingerprint,
            history_fingerprint=history_fingerprint_from_snapshot(
                database=request.database,
                search_string=request.search_string,
                filters=request.filters,
            ),
            status=STATUS_PENDING,
            created_at=now,
        )
        try:
            saved = await self.repo.create_task(entity)
        except IntegrityError:
            # 唯一约束是跨请求的最终裁决：竞争者创建成功后，本请求回滚并复用它。
            await self.repo.session.rollback()
            existing = await self.repo.get_task_by_fingerprint(fingerprint)
            if existing is None:
                raise
            rerun = await self.rerun_task(existing.id)
            return LiteratureSearchTaskCreateResult(
                **rerun.task.model_dump(),
                operation="reused",
                change=rerun.change,
                new_result_id=rerun.new_result_id,
            )
        await self._run_task(saved, request.retmax)
        task = await self.get_task(saved.id)
        return LiteratureSearchTaskCreateResult(
            **task.model_dump(),
            operation="created",
            change=None,
            new_result_id=task.latest_result_id or 0,
        )

    async def _find_legacy_task_by_fingerprint(
        self, fingerprint: str
    ) -> LiteratureSearchTask | None:
        """以纯函数比对旧快照；只给首个匹配任务加指纹，不处理其他审计行。"""
        for task in await self.repo.list_tasks_for_fingerprint_matching():
            if strategy_fingerprint_from_snapshot(
                database=task.database,
                search_string=task.search_string,
                filters=task.filters,
                retmax=task.retmax,
                user_edits=task.user_edits,
                model_version=task.model_version,
                structured_query=task.structured_query,
                original_query=task.original_query,
            ) == fingerprint:
                task.strategy_fingerprint = fingerprint
                try:
                    return await self.repo.save_task(task)
                except IntegrityError:
                    await self.repo.session.rollback()
                    return await self.repo.get_task_by_fingerprint(fingerprint)
        return None

    async def get_task(self, id: int) -> LiteratureSearchTaskRead:
        """返回任务详情，含按版本升序排列的结果版本时间线。"""
        entity = await self.repo.get_task(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        return await self._to_task_read(entity)

    async def list_tasks(
        self, offset: int = 0, limit: int = 20
    ) -> LiteratureSearchTaskList:
        """分页返回任务历史（创建时间倒序），列表不携带条目明细。"""
        tasks, total = await self.repo.list_tasks(offset=offset, limit=limit)
        items = [await self._to_task_read(task) for task in tasks]
        return LiteratureSearchTaskList(
            total=total, offset=offset, limit=limit, items=items
        )

    async def list_history(
        self, offset: int = 0, limit: int = 20
    ) -> LiteratureSearchHistoryList:
        """返回每个 canonical 策略的最新工作记录。

        分组、取最新和分页均由 repository 的 SQL 窗口查询完成；旧任务及其
        结果快照仍保持独立审计行，read-model 只决定主历史页的可见入口。
        """
        page_tasks, total = await self.repo.list_history(offset=offset, limit=limit)
        entries: list[LiteratureSearchHistoryEntry] = []
        for task in page_tasks:
            task_read = await self._to_task_read(task)
            entries.append(
                LiteratureSearchHistoryEntry(
                    id=task_read.id,
                    original_query=task_read.original_query,
                    result_count=task_read.result_count,
                    status=task_read.status,
                    error_message=task_read.error_message,
                    searched_at=task_read.searched_at,
                    latest_result_id=task_read.latest_result_id,
                    latest_change=(task_read.versions[-1].change if task_read.versions else None),
                )
            )
        return LiteratureSearchHistoryList(
            total=total, offset=offset, limit=limit, items=entries
        )

    async def rerun_task(
        self,
        id: int,
        *,
        retmax: int | None = None,
    ) -> LiteratureSearchTaskRerun:
        """重跑任务：按持久化的输入快照重新检索，创建新结果版本，不覆盖旧版本。

        设计说明：重跑前对比旧版本（get_latest_version）与新结果，输出变化摘要
        （新增/减少条目数与 PMID 集合），满足"结果变化有提示"。首次重跑时旧版本
        即创建时的版本 1；任务从未成功过（如失败任务重试）时无对比基线，
        change 为 None。
        """
        entity = await self.repo.get_task(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        previous = await self.repo.get_latest_version(id)
        await self._run_task(entity, retmax if retmax is not None else entity.retmax)
        updated = await self.repo.get_task(id)
        new_version = await self.repo.get_latest_version(id)
        if updated is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        change = None
        if (
            previous is not None
            and new_version is not None
            and new_version.id != previous.id
        ):
            change = await self._build_change(previous, new_version)
        task_read = await self._to_task_read(updated)
        return LiteratureSearchTaskRerun(
            task=task_read,
            change=change,
            new_result_id=new_version.result_id if new_version is not None else 0,
        )

    async def export_strategy(self, id: int) -> SearchStrategyExport:
        """导出 PRISMA-compliant 检索策略（数据库、检索日期、查询串、结果数）。

        设计说明：检索日期取最近一次成功执行的 searched_at；任务失败或从未成功
        时没有可导出的检索日期，直接抛 404，避免导出伪造的时间与结果数。
        """
        entity = await self.repo.get_task(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        if entity.searched_at is None:
            raise NotFoundError(
                f"LiteratureSearchTask {id} has no successful search to export"
            )
        return SearchStrategyExport(
            original_query=entity.original_query,
            database=entity.database,
            search_string=entity.search_string,
            searched_at=entity.searched_at,
            result_count=entity.result_count,
            filters=entity.filters,
            model_version=entity.model_version,
            status=_coerce_status(entity.status),
        )

    # ------------------------------------------------------------------
    # 任务执行与版本管理
    # ------------------------------------------------------------------

    async def _run_task(self, entity: LiteratureSearchTask, retmax: int) -> None:
        """执行一次检索并把结果版本挂到任务上。

        状态机：running →（成功）succeeded 或（失败）failed。失败记录
        error_message 且不创建结果版本；所有失败仅由执行层异常触发，不伪造结果。
        """
        entity.status = STATUS_RUNNING
        await self.repo.save_task(entity)
        try:
            items, total_count = await self.pubmed_executor.execute(
                entity.search_string, retmax=retmax
            )
        except PubMedError as exc:
            # 执行层异常统一收敛为 failed：PubMed 调用失败、超时、网络异常等。
            entity.status = STATUS_FAILED
            entity.error_message = str(exc)
            await self.repo.save_task(entity)
            return
        result_entity = await self.repo.create_result(
            LiteratureSearchResult(
                query=entity.search_string,
                total_count=total_count,
                items_json=json.dumps(
                    [item.model_dump() for item in items], ensure_ascii=False
                ),
            )
        )
        latest = await self.repo.get_latest_version(entity.id)
        next_version = (latest.version + 1) if latest is not None else 1
        await self.repo.create_result_version(entity.id, result_entity.id, next_version)
        entity.status = STATUS_SUCCEEDED
        entity.result_count = total_count
        entity.searched_at = datetime.now(UTC)
        entity.latest_result_id = result_entity.id
        entity.error_message = None
        await self.repo.save_task(entity)

    async def _build_change(
        self,
        previous: LiteratureSearchResultVersion,
        current: LiteratureSearchResultVersion,
    ) -> SearchResultChange:
        """对比新旧两个版本，输出结果变化摘要。

        设计说明：对比基于 PMID 集合（真实检索标识符），不比较标题/摘要等易变
        文本；新增 = 新版本有而旧版本没有的 PMID，减少 = 相反方向。result_count
        变化反映 ESearch 命中的时间漂移。
        """
        prev_result = await self.repo.get_result(previous.result_id)
        cur_result = await self.repo.get_result(current.result_id)
        prev_pmids = self._pmids_from_result(prev_result)
        cur_pmids = self._pmids_from_result(cur_result)
        added = sorted(cur_pmids - prev_pmids)
        removed = sorted(prev_pmids - cur_pmids)
        prev_count = prev_result.total_count if prev_result is not None else 0
        cur_count = cur_result.total_count if cur_result is not None else 0
        return SearchResultChange(
            previous_count=prev_count,
            current_count=cur_count,
            count_delta=cur_count - prev_count,
            added_count=len(added),
            removed_count=len(removed),
            added_pmids=added,
            removed_pmids=removed,
        )

    @staticmethod
    def _pmids_from_result(entity: LiteratureSearchResult | None) -> set[str]:
        if entity is None:
            return set()
        items = [
            CitationItem.model_validate(item) for item in json.loads(entity.items_json)
        ]
        return {item.pmid for item in items}

    async def _to_task_read(
        self, entity: LiteratureSearchTask
    ) -> LiteratureSearchTaskRead:
        versions = await self.repo.get_task_versions(entity.id)
        version_reads: list[LiteratureSearchTaskVersion] = []
        prev_ref: LiteratureSearchResultVersion | None = None
        for ref in versions:
            result = await self.repo.get_result(ref.result_id)
            version_reads.append(
                LiteratureSearchTaskVersion(
                    version=ref.version,
                    result_id=ref.result_id,
                    searched_at=ref.created_at,
                    result_count=result.total_count if result is not None else 0,
                    change=await self._build_change(prev_ref, ref)
                    if prev_ref is not None
                    else None,
                )
            )
            prev_ref = ref
        return LiteratureSearchTaskRead(
            id=entity.id,
            original_query=entity.original_query,
            structured_query=entity.structured_query,
            search_string=entity.search_string,
            database=entity.database,
            result_count=entity.result_count,
            retmax=entity.retmax,
            filters=entity.filters,
            model_version=entity.model_version,
            user_edits=entity.user_edits,
            status=_coerce_status(entity.status),
            error_message=entity.error_message,
            created_at=entity.created_at,
            searched_at=entity.searched_at,
            latest_result_id=entity.latest_result_id,
            strategy_fingerprint=entity.strategy_fingerprint,
            versions=version_reads,
        )

    async def execute_search(
        self, request: SearchExecuteRequest
    ) -> LiteratureSearchResultRead:
        """执行 PubMed 检索并把结果落库。

        反幻觉边界：条目 verified 标记由 pubmed_executor 依据真实 EFetch 响应
        打标，这里只做持久化与读取，不修改任何验证状态。
        """
        items, total_count = await self.pubmed_executor.execute(
            request.boolean_query, retmax=request.retmax
        )
        entity = LiteratureSearchResult(
            query=request.boolean_query,
            total_count=total_count,
            items_json=json.dumps(
                [item.model_dump() for item in items], ensure_ascii=False
            ),
        )
        saved = await self.repo.create_result(entity)
        return self._to_result_read(saved, items)

    async def get_result(self, id: int) -> LiteratureSearchResultRead:
        entity = await self.repo.get_result(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {id}")
        return self._to_result_read(entity)

    # ------------------------------------------------------------------
    # R2-WP05：筛选、排序与分页
    # ------------------------------------------------------------------

    async def get_result_page(
        self, id: int, params: ResultQueryParams
    ) -> LiteratureSearchResultPage:
        """按筛选/排序/分页参数返回结果页。

        流程：读取 items_json 快照 → 并入用户态 → 组合筛选 → 排序（带
        sort_reason）→ 切片。筛选与排序都在内存完成，结果快照不可写回；
        分页切片发生在排序之后，保证"排序理由可解释"且翻页稳定。
        """
        entity = await self.repo.get_result(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {id}")
        items = await self._project_result_items(entity, params.duplicate_mode)
        state_map = await self.repo.get_item_states(id)
        filtered = filtering.apply_filters(
            items,
            params,
            state_by_pmid=lambda pmid: self._state_tuple(state_map.get(pmid)),
        )
        ranked = ranking.sort_items(
            filtered,
            params,
            current_year=datetime.now(UTC).year,
            custom_order=self._custom_order_map(state_map),
        )
        start = (params.page - 1) * params.page_size
        page_items = ranked[start : start + params.page_size]
        library_items = {
            item.pmid: item
            for item in await LibraryItemRepository(self.session).list_by_pmids(
                [entry.item.pmid for entry in page_items]
            )
        }
        return LiteratureSearchResultPage(
            result_id=entity.id,
            query=entity.query,
            total_count=entity.total_count,
            filtered_total=len(filtered),
            page=params.page,
            page_size=params.page_size,
            sort=params.sort,
            duplicate_mode=params.duplicate_mode,
            hidden_duplicate_count=len(self._result_items(entity)) - len(items),
            items=[
                self._ranked_with_state(entry, state_map).model_copy(
                    update={
                        "library_item": (
                            LibraryItemRead.model_validate(library_items[entry.item.pmid])
                            if entry.item.pmid in library_items
                            else None
                        )
                    }
                )
                for entry in page_items
            ],
        )

    async def update_item_state(
        self, result_id: int, pmid: str, request: ItemStateUpdate
    ) -> ItemStateRead:
        """写入单条结果的用户态（saved / read_status / tags / custom 序号）。

        先校验结果与 PMID 存在，避免对不存在的结果写用户态；三个状态字段
        只在请求提供了值时才覆盖（None 表示"本次不改"），已存在的旧值保留。
        """
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        if not any(item.pmid == pmid for item in self._result_items(result)):
            raise NotFoundError(f"PMID not found in result: {pmid}")
        existing = await self.repo.get_item_state(result_id, pmid)
        # tags 处理与 saved/read_status 一致：请求未提供时保留旧值，无旧值则空标签。
        tags = (
            existing.tags_json
            if request.tags is None and existing is not None
            else serialize_tags(request.tags or [])
        )
        entity = await self.repo.upsert_item_state(
            LiteratureSearchItemState(
                result_id=result_id,
                pmid=pmid,
                saved=request.saved
                if request.saved is not None
                else (existing.saved if existing is not None else False),
                read_status=request.read_status
                if request.read_status is not None
                else (
                    existing.read_status
                    if existing is not None
                    else DEFAULT_READ_STATUS
                ),
                tags_json=tags,
                custom_order_index=(
                    request.custom_order_index
                    if request.custom_order_index is not None
                    else existing.custom_order_index
                    if existing is not None
                    else None
                ),
            )
        )
        return self._to_state_read(entity)

    async def get_item_state(self, result_id: int, pmid: str) -> ItemStateRead:
        """读取单条结果的用户态；从未写入过时返回默认值（不报错）。"""
        entity = await self.repo.get_item_state(result_id, pmid)
        if entity is None:
            return ItemStateRead(
                saved=False,
                # DEFAULT_READ_STATUS 值为 "unread"，此处用字面量以符合 Literal 类型。
                read_status="unread",
                tags=[],
                custom_order_index=None,
            )
        return self._to_state_read(entity)

    # ------------------------------------------------------------------
    # R2-WP08：推荐阅读顺序
    # ------------------------------------------------------------------

    async def generate_reading_order(
        self,
        result_id: int,
        manual_order: list[str],
        duplicate_mode: Literal["all", "consolidated"] = "all",
    ) -> ReadingOrderRead:
        """生成基于规则特征的分层阅读顺序。

        review-paper 融合：分类依据 publication_types（真实字段）与年份/相关度
        信号；search-lit 融合：相关度只用 verified 与检索序（不编造被引量）；
        manage-refs 融合：已保存的人工顺序优先于算法顺序（重新生成不覆盖）。

        流程：读取结果快照 → 读人工顺序 → 规则分类（纯函数）→ 算法排序 →
        应用人工顺序（若存在）→ 编号 priority 1..n → 组装响应。
        """
        entity = await self.repo.get_result(result_id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        items = await self._project_result_items(entity, duplicate_mode)
        if not items:
            return ReadingOrderRead(
                result_id=result_id,
                order_source="rule",
                duplicate_mode=duplicate_mode,
                generated_at=datetime.now(UTC),
                items=[],
            )

        # 读取全文状态：批量按 PMID 查询本地知识库，未收藏的条目为 None。
        fulltext_map = {
            item.pmid: item.fulltext_status
            for item in await LibraryItemRepository(self.session).list_by_pmids(
                [item.pmid for item in items]
            )
        }
        current_year = datetime.now(UTC).year
        total = len(items)
        classified = [
            classify_reading_item(
                item,
                ReadingContext(
                    current_year=current_year,
                    position=position,
                    total_items=total,
                    fulltext_status=fulltext_map.get(item.pmid),
                ),
            )
            for position, item in enumerate(items)
        ]

        # 人工顺序优先：POST 请求携带的 manual_order 覆盖算法顺序；
        # 未携带（空列表）时读库中已保存的人工顺序（重新生成不覆盖）。
        effective_manual = manual_order or await self._saved_manual_order(result_id, duplicate_mode)
        algorithm_ranked = rank_reading_order(classified)
        ordered = apply_manual_order(algorithm_ranked, effective_manual)
        # order_source 收敛为 Literal["rule", "manual"]：有人工顺序则 manual 优先。
        order_source: Literal["rule", "manual"] = (
            "manual" if effective_manual else "rule"
        )

        return ReadingOrderRead(
            result_id=result_id,
            order_source=order_source,
            duplicate_mode=duplicate_mode,
            generated_at=datetime.now(UTC),
            items=[
                ReadingOrderItem(
                    pmid=entry.pmid,
                    category=entry.category,
                    priority=index + 1,
                    reason=entry.reason,
                    evidence_features=list(entry.evidence_features),
                    title=next(
                        (item.title for item in items if item.pmid == entry.pmid), None
                    ),
                    year=entry.year,
                )
                for index, entry in enumerate(ordered)
            ],
        )

    async def save_reading_order(
        self, result_id: int, manual_order: list[str], duplicate_mode: Literal["all", "consolidated"] = "all"
    ) -> ReadingOrderRead:
        """保存用户拖拽后的人工顺序并返回应用该顺序的阅读顺序。

        manage-refs 融合：只保存用户态（PMID 顺序 JSON），不改写结果快照；
        返回结果由保存后的人工顺序驱动（order_source="manual"）。对不存在
        的结果快照直接 404，避免给不存在的引用挂人工顺序。
        """
        entity = await self.repo.get_result(result_id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        now = datetime.now(UTC)
        # 人工顺序全量替换：结果快照中不存在的 PMID 由 apply_manual_order 忽略，
        # 但这里仍原样保存用户提交的顺序，保证"用户拖拽的原始顺序"完整留存。
        await self.repo.upsert_reading_order(
            LiteratureReadingOrder(
                result_id=result_id,
                duplicate_mode=duplicate_mode,
                manual_order_json=json.dumps(manual_order, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
        )
        return await self.generate_reading_order(result_id, manual_order, duplicate_mode)

    async def _saved_manual_order(self, result_id: int, duplicate_mode: str = "all") -> list[str]:
        """读取库中已保存的人工顺序；不存在时返回空列表。

        manual_order_json 是 JSON 数组字符串，解析失败（旧数据/手工编辑）
        时兜底为空列表，保证损坏的人工顺序不阻塞阅读顺序生成。
        """
        saved = await self.repo.get_reading_order(result_id, duplicate_mode)
        if saved is None:
            return []
        try:
            value = json.loads(saved.manual_order_json)
        except ValueError:
            return []
        if not isinstance(value, list):
            return []
        return [str(pmid) for pmid in value]

    async def deduplicate_task(self, task_id: int) -> DuplicateGroupList:
        """跨各任务当前快照生成可撤销决策；不会改写或删除原始检索记录。"""
        if await self.repo.get_task(task_id) is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {task_id}")
        await self.repo.delete_groups_for_task(task_id)
        for candidate in find_duplicate_candidates(await self._dedup_records()):
            canonical = select_canonical_record(candidate.records)
            canonical_result_id = int(canonical.record_id.split(":", maxsplit=1)[0])
            group = LiteratureDuplicateGroup(
                trigger_task_id=task_id,
                match_method=candidate.match_method,
                confidence=candidate.confidence,
                status="auto_merged"
                if candidate.confidence == "clear"
                else "pending_resolution",
            )
            for record in candidate.records:
                group.members.append(
                    LiteratureDuplicateGroupMember(
                        result_id=int(record.record_id.split(":", maxsplit=1)[0]),
                        record_pmid=record.item.pmid,
                        source_search_ids_json=json.dumps(record.source_search_ids),
                        canonical_result_id=(
                            canonical_result_id
                            if candidate.confidence == "clear"
                            else None
                        ),
                        canonical_record_pmid=(
                            canonical.item.pmid
                            if candidate.confidence == "clear"
                            else None
                        ),
                    )
                )
            await self.repo.create_duplicate_group(group)
        return await self.list_duplicate_groups()

    async def deduplicate_result(self, result_id: int) -> DeduplicationSummary:
        """扫描一个不可变结果快照，并仅维护该快照的去重工作视图。"""
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        task = await self.repo.get_task_for_result(result_id)
        if task is None:
            raise NotFoundError(f"LiteratureSearchTask not found for result: {result_id}")
        records = self._result_dedup_records(result)
        for candidate in find_duplicate_candidates(records):
            fingerprint = self._candidate_fingerprint(candidate)
            if (
                await self.repo.get_result_duplicate_group_by_fingerprint(
                    result_id, fingerprint
                )
                is not None
            ):
                continue
            canonical = select_canonical_record(candidate.records)
            group = LiteratureDuplicateGroup(
                trigger_task_id=task.id,
                result_id=result_id,
                fingerprint=fingerprint,
                match_method=candidate.match_method,
                confidence=candidate.confidence,
                status=(
                    "auto_merged"
                    if candidate.confidence == "clear"
                    else "pending_resolution"
                ),
            )
            for record in candidate.records:
                group.members.append(
                    LiteratureDuplicateGroupMember(
                        result_id=result_id,
                        record_pmid=record.item.pmid,
                        record_key=record.record_id,
                        position=self._record_position(record.record_id),
                        source_search_ids_json=json.dumps([task.id]),
                        canonical_result_id=(
                            result_id if candidate.confidence == "clear" else None
                        ),
                        canonical_record_pmid=(
                            canonical.item.pmid
                            if candidate.confidence == "clear"
                            else None
                        ),
                        canonical_record_key=(
                            canonical.record_id if candidate.confidence == "clear" else None
                        ),
                    )
                )
            await self.repo.create_duplicate_group(group)
        # 无论是否产生组都打上扫描标记，使"已扫描但无重复"与"从未扫描"可区分。
        if result.dedup_scanned_at is None:
            result.dedup_scanned_at = datetime.now(UTC)
            await self.repo.save_result(result)
        return await self.get_deduplication_summary(result_id)

    async def get_deduplication_summary(self, result_id: int) -> DeduplicationSummary:
        """读取摘要时绝不触发扫描，未扫描快照返回稳定的空摘要。"""
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        groups, _total = await self.repo.list_result_duplicate_groups(
            result_id, 0, 10000, "all"
        )
        scanned_count = len(self._result_items(result))
        hidden = sum(
            len(group.members) - 1
            for group in groups
            if group.status in {"auto_merged", "resolved_merged"}
        )
        return DeduplicationSummary(
            result_id=result_id,
            scanned_count=scanned_count,
            source_visible_count=scanned_count,
            consolidated_visible_count=scanned_count - hidden,
            hidden_record_count=hidden,
            clear_group_count=sum(group.confidence == "clear" for group in groups),
            pending_group_count=sum(
                group.status == "pending_resolution" for group in groups
            ),
            resolved_merge_group_count=sum(
                group.status == "resolved_merged" for group in groups
            ),
            resolved_keep_all_group_count=sum(
                group.status == "resolved_keep_all" for group in groups
            ),
            has_scan=result.dedup_scanned_at is not None,
            generated_at=result.dedup_scanned_at,
        )

    async def list_result_duplicate_groups(
        self, result_id: int, offset: int, limit: int, status: str | None = "all"
    ) -> DuplicateGroupPage:
        """分页返回单一结果快照的重复组，不混入任何历史结果。

        status 默认 "all"（不加过滤）；过滤时按组状态精确匹配。
        """
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        groups, total = await self.repo.list_result_duplicate_groups(
            result_id, offset, limit, status
        )
        items = self._result_items(result)
        return DuplicateGroupPage(
            total=total,
            offset=offset,
            limit=limit,
            items=[
                self._enrich_duplicate_group_read(
                    self._to_duplicate_group_read(group), items
                )
                for group in groups
            ],
        )

    async def resolve_result_duplicate_group(
        self, result_id: int, group_id: int, request: ResultDuplicateResolutionRequest
    ) -> ResultDuplicateResolutionRead:
        group = await self.repo.get_duplicate_group(group_id)
        if group is None or group.result_id != result_id:
            raise NotFoundError(f"Duplicate group not found for result: {result_id}")
        canonical_pmid: str | None = None
        if request.action == "merge":
            if not request.canonical_record_key:
                raise HTTPException(
                    status_code=422, detail="merge requires canonical_record_key"
                )
            canonical_member = next(
                (
                    member
                    for member in group.members
                    if member.record_key == request.canonical_record_key
                ),
                None,
            )
            if canonical_member is None:
                raise HTTPException(
                    status_code=422,
                    detail="canonical_record_key is not a member of the duplicate group",
                )
            canonical_pmid = canonical_member.record_pmid
        legacy_action = {
            "merge": "keep_record",
            "keep_all": "keep_all",
            "undo": "undo",
        }[request.action]
        resolved = await self.resolve_duplicate_group(
            group_id,
            DuplicateResolveRequest(
                action=cast(
                    "Literal['keep_record', 'keep_all', 'merge_all', 'undo']",
                    legacy_action,
                ),
                canonical_result_id=result_id if request.action == "merge" else None,
                canonical_record_pmid=canonical_pmid,
                resolved_by=request.resolved_by,
            ),
        )
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        return ResultDuplicateResolutionRead(
            group=self._enrich_duplicate_group_read(resolved, self._result_items(result)),
            summary=await self.get_deduplication_summary(result_id),
        )

    async def _project_result_items(self, result: LiteratureSearchResult, duplicate_mode: str) -> list[CitationItem]:
        items = self._result_items(result)
        if duplicate_mode == "all":
            return items
        groups, _ = await self.repo.list_result_duplicate_groups(result.id, 0, 10000, "all")
        hidden_positions: set[int] = set()
        for group in groups:
            if group.status not in {"auto_merged", "resolved_merged"}:
                continue
            canonical_key = next((member.canonical_record_key for member in group.members if member.canonical_record_key), None)
            if canonical_key is None:
                canonical_key = next((member.record_key for member in group.members if member.canonical_record_pmid == member.record_pmid), None)
            hidden_positions.update(member.position - 1 for member in group.members if member.position is not None and member.record_key != canonical_key)
        return [item for position, item in enumerate(items) if position not in hidden_positions]

    async def list_duplicate_groups(self) -> DuplicateGroupList:
        return DuplicateGroupList(
            items=[
                self._to_duplicate_group_read(group)
                for group in await self.repo.list_duplicate_groups()
            ]
        )

    async def resolve_duplicate_group(
        self, group_id: int, request: DuplicateResolveRequest
    ) -> DuplicateGroupRead:
        group = await self.repo.get_duplicate_group(group_id)
        if group is None:
            raise NotFoundError(f"Duplicate group not found: {group_id}")
        if request.action == "undo":
            if group.resolution is not None:
                await self.repo.delete_duplicate_resolution(group.resolution)
            if group.confidence == "fuzzy":
                # fuzzy 仅是待人工确认的候选，撤销后必须抹去人工决策，恢复全部可见。
                for member in group.members:
                    member.canonical_result_id = None
                    member.canonical_record_pmid = None
                    member.canonical_record_key = None
                group.status = "pending_resolution"
            else:
                # clear 是系统确定性归并；撤销人工改选时须从不可变快照重算，不能沿用旧选择。
                clear_canonical = await self._select_clear_group_canonical(group)
                if clear_canonical is None:
                    # 旧跨任务组没有结果级稳定键，保留兼容行为且避免撤销接口异常。
                    for member in group.members:
                        member.canonical_result_id = None
                        member.canonical_record_pmid = None
                        member.canonical_record_key = None
                else:
                    for member in group.members:
                        member.canonical_result_id = group.result_id
                        member.canonical_record_pmid = clear_canonical.item.pmid
                        member.canonical_record_key = clear_canonical.record_id
                group.status = "auto_merged"
            await self.repo.save_duplicate_group(group)
            return self._to_duplicate_group_read(group)

        canonical = self._resolve_canonical_member(group, request)
        should_merge = request.action in {"keep_record", "merge_all"}
        for member in group.members:
            member.canonical_result_id = canonical.result_id if should_merge else None
            member.canonical_record_pmid = (
                canonical.record_pmid if should_merge else None
            )
            member.canonical_record_key = canonical.record_key if should_merge else None
        group.status = "resolved_merged" if should_merge else "resolved_keep_all"
        group.resolution = await self.repo.replace_duplicate_resolution(
            LiteratureDuplicateResolution(
                group_id=group.id,
                resolved_action=request.action,
                resolved_by=request.resolved_by,
            )
        )
        await self.repo.save_duplicate_group(group)
        return self._to_duplicate_group_read(group)

    async def _dedup_records(self) -> list[DedupRecord]:
        task_results = await self.repo.latest_task_results()
        sources: dict[int, list[int]] = {}
        results: dict[int, LiteratureSearchResult] = {}
        for task_id, result in task_results:
            sources.setdefault(result.id, []).append(task_id)
            results[result.id] = result
        return [
            DedupRecord(
                record_id=f"{result_id}:{item.pmid}",
                item=item,
                source_search_ids=tuple(sorted(sources[result_id])),
            )
            for result_id, result in results.items()
            for item in self._result_items(result)
        ]

    async def _select_clear_group_canonical(
        self, group: LiteratureDuplicateGroup
    ) -> DedupRecord | None:
        """从结果快照重建 clear 组规范记录，缺少结果级身份时兼容旧分组。"""
        if group.result_id is None:
            return None
        result = await self.repo.get_result(group.result_id)
        if result is None:
            return None
        records_by_key = {
            record.record_id: record for record in self._result_dedup_records(result)
        }
        records = [
            records_by_key[member.record_key]
            for member in group.members
            if member.record_key in records_by_key
        ]
        if len(records) != len(group.members):
            return None
        return select_canonical_record(tuple(records))

    @staticmethod
    def _result_dedup_records(result: LiteratureSearchResult) -> list[DedupRecord]:
        """为同一快照的每个原始位置分配稳定键，避免相同 PMID 冲突。"""
        return [
            DedupRecord(
                record_id=f"{result.id}:{position}:{item.pmid}",
                item=item,
                source_search_ids=(),
            )
            for position, item in enumerate(LiteratureSearchService._result_items(result))
        ]

    @staticmethod
    def _candidate_fingerprint(candidate: DuplicateCandidate) -> str:
        """用匹配规则和稳定记录键识别不可变快照中的同一候选组。"""
        record_ids = sorted(record.record_id for record in candidate.records)
        payload = json.dumps(
            {"method": candidate.match_method, "record_keys": record_ids},
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _record_position(record_key: str) -> int:
        """从受控 record_key 恢复结果内 1-based 位置。"""
        return int(record_key.split(":", maxsplit=2)[1]) + 1

    @staticmethod
    def _resolve_canonical_member(
        group: LiteratureDuplicateGroup, request: DuplicateResolveRequest
    ) -> LiteratureDuplicateGroupMember:
        if request.action in {"keep_all", "merge_all"}:
            return group.members[0]
        if request.canonical_result_id is None or request.canonical_record_pmid is None:
            raise ValueError(
                "keep_record requires canonical_result_id and canonical_record_pmid"
            )
        for member in group.members:
            if (
                member.result_id == request.canonical_result_id
                and member.record_pmid == request.canonical_record_pmid
            ):
                return member
        raise ValueError("canonical record is not a member of the duplicate group")

    @staticmethod
    def _to_duplicate_group_read(group: LiteratureDuplicateGroup) -> DuplicateGroupRead:
        canonical_key = next(
            (
                member.canonical_record_key
                for member in group.members
                if member.canonical_record_key is not None
            ),
            None,
        )
        is_collapsed = group.status in {"auto_merged", "resolved_merged"}
        return DuplicateGroupRead(
            id=group.id,
            trigger_task_id=group.trigger_task_id,
            result_id=group.result_id,
            match_method=cast(
                "Literal['pmid', 'doi', 'title_normalized', 'author_year', 'manual']",
                group.match_method,
            ),
            confidence=cast("Literal['clear', 'fuzzy']", group.confidence),
            status=cast(
                "Literal['pending_resolution', 'auto_merged', 'resolved_keep_all', 'resolved_merged']",
                group.status,
            ),
            created_at=group.created_at,
            match_explanation=LiteratureSearchService._match_explanation(group.match_method),
            canonical_record_key=canonical_key,
            members=[
                DuplicateGroupMemberRead(
                    result_id=member.result_id,
                    record_pmid=member.record_pmid,
                    record_key=member.record_key,
                    position=member.position,
                    pmid=member.record_pmid,
                    is_canonical=(
                        member.record_key is not None
                        and member.record_key == canonical_key
                    ),
                    visible_in_consolidated_view=(
                        not is_collapsed
                        or member.record_key is None
                        or member.record_key == canonical_key
                    ),
                    canonical_result_id=member.canonical_result_id,
                    canonical_record_pmid=member.canonical_record_pmid,
                    source_search_ids=json.loads(member.source_search_ids_json),
                )
                for member in group.members
            ],
            resolution=None
            if group.resolution is None
            else DuplicateResolutionRead(
                resolved_at=group.resolution.resolved_at,
                resolved_action=cast(
                    "Literal['keep_record', 'keep_all', 'merge_all', 'undo']",
                    group.resolution.resolved_action,
                ),
                resolved_by=group.resolution.resolved_by,
            ),
        )

    @staticmethod
    def _match_explanation(match_method: str) -> str:
        return {
            "pmid": "PMID exact match",
            "doi": "Normalized DOI exact match",
            "title_normalized": "Normalized title match; manual confirmation required",
            "author_year": "First author and year match; manual confirmation required",
        }.get(match_method, "Manual duplicate decision")

    @staticmethod
    def _enrich_duplicate_group_read(group: DuplicateGroupRead, items: list[CitationItem]) -> DuplicateGroupRead:
        by_position = {index + 1: item for index, item in enumerate(items)}
        return group.model_copy(update={"members": [member.model_copy(update={
            "doi": by_position[member.position].doi if member.position in by_position else None,
            "title": by_position[member.position].title if member.position in by_position else None,
            "authors": list(by_position[member.position].authors) if member.position in by_position else [],
            "journal": by_position[member.position].journal if member.position in by_position else None,
            "year": by_position[member.position].year if member.position in by_position else None,
            "publication_types": list(by_position[member.position].publication_types) if member.position in by_position else [],
            "verified": by_position[member.position].verified if member.position in by_position else False,
            "has_abstract": by_position[member.position].has_abstract if member.position in by_position else False,
            "withdrawn": by_position[member.position].withdrawn if member.position in by_position else False,
        }) for member in group.members]})

    @staticmethod
    def _result_items(entity: LiteratureSearchResult) -> list[CitationItem]:
        """从结果快照解析条目列表（仅用于 PMID 存在性校验）。"""
        return [
            CitationItem.model_validate(item) for item in json.loads(entity.items_json)
        ]

    @staticmethod
    def _state_tuple(
        state: LiteratureSearchItemState | None,
    ) -> tuple[bool, str, list[str]]:
        """把用户态实体收敛为 filtering 回调签名 (saved, read_status, tags)。"""
        if state is None:
            return False, DEFAULT_READ_STATUS, []
        return state.saved, state.read_status, deserialize_tags(state.tags_json)

    @staticmethod
    def _custom_order_map(
        state_map: dict[str, LiteratureSearchItemState],
    ) -> dict[str, int]:
        """提取 {pmid: 自定义序号}，供 ranking.custom 排序使用。"""
        return {
            pmid: state.custom_order_index
            for pmid, state in state_map.items()
            if state.custom_order_index is not None
        }

    @staticmethod
    def _ranked_with_state(
        entry: RankedCitationItem, state_map: dict[str, LiteratureSearchItemState]
    ) -> RankedCitationItem:
        """为排序结果并入用户态（分页响应每个条目直接展示）。"""
        state = state_map.get(entry.item.pmid)
        return RankedCitationItem(
            item=entry.item,
            sort_reason=entry.sort_reason,
            state=None
            if state is None
            else LiteratureSearchService._to_state_read(state),
        )

    @staticmethod
    def _to_state_read(state: LiteratureSearchItemState) -> ItemStateRead:
        # read_status 在 DB 层是 str，收敛为 ReadStatus Literal（非法值按 unread 兜底，
        # 与 DEFAULT_READ_STATUS 语义一致；正常数据不会走到兜底分支）。
        # 显式分支赋值：read 直接收敛为 Literal；其余（含非法值）兜底 unread，
        # 与 DEFAULT_READ_STATUS（"unread"）语义一致。
        if state.read_status == "read":
            read_status: ReadStatus = "read"
        else:
            read_status = "unread"
        return ItemStateRead(
            saved=state.saved,
            read_status=read_status,
            tags=deserialize_tags(state.tags_json),
            custom_order_index=state.custom_order_index,
        )

    async def bibtex(self, id: int) -> str:
        """导出指定检索结果的 BibTeX 文本。

        条目来自数据库持久化的 items_json（当时检索的真实验证状态），导出不
        重新调用 PubMed，也不补全任何缺失字段。
        """
        entity = await self.repo.get_result(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {id}")
        items = [
            CitationItem.model_validate(item) for item in json.loads(entity.items_json)
        ]
        return to_bibtex(items)

    @staticmethod
    def _to_result_read(
        entity: LiteratureSearchResult,
        items: list[CitationItem] | None = None,
    ) -> LiteratureSearchResultRead:
        if items is None:
            items = [
                CitationItem.model_validate(item)
                for item in json.loads(entity.items_json)
            ]
        return LiteratureSearchResultRead(
            id=entity.id,
            query=entity.query,
            total_count=entity.total_count,
            created_at=entity.created_at,
            items=items,
        )

    @staticmethod
    async def _extract_with_configured_model(prompt: str) -> str:
        from app.core.config import settings

        message = [ChatMessage(role="user", content=prompt)]
        if settings.DEFAULT_MODEL_PROVIDER == "ollama":
            async with OllamaClient.from_settings() as client:
                return (await client.chat(message)).text
        async with LLMClient.from_settings() as client:
            return (await client.chat(message)).text

    @staticmethod
    def _rule_candidate(raw_topic: str) -> SearchIntentCandidate:
        pico = extract_curated_pico(raw_topic)
        candidate = SearchIntentCandidate(
            topic=raw_topic,
            disease=pico.population,
            intervention=pico.intervention,
            comparison=pico.comparison,
            outcome=pico.outcome,
        )
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)),
                relative.group(0),
            )
        return candidate

    @staticmethod
    def _fill_missing_pico_fields(
        candidate: SearchIntentCandidate, fallback: SearchIntentCandidate
    ) -> SearchIntentCandidate:
        """Keep model output first, using only curated fallback phrases for blanks."""
        return candidate.model_copy(
            update={
                "disease": candidate.disease or fallback.disease,
                "intervention": candidate.intervention or fallback.intervention,
                "comparison": candidate.comparison or fallback.comparison,
                "outcome": candidate.outcome or fallback.outcome,
            }
        )

    @staticmethod
    def _constrain_candidate(
        candidate: SearchIntentCandidate, raw_topic: str
    ) -> SearchIntentCandidate:
        if not candidate.topic.strip() or len(candidate.topic) > len(raw_topic) * 3:
            candidate.topic = raw_topic
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)),
                relative.group(0),
            )
        return candidate

    @staticmethod
    def _parse_year_count(value: str) -> int:
        if value.isdigit():
            return int(value)
        numerals = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        if value == "十":
            return 10
        if value.startswith("十"):
            return 10 + numerals[value[1]]
        if value.endswith("十"):
            return numerals[value[0]] * 10
        if "十" in value:
            return numerals[value[0]] * 10 + numerals[value[2]]
        return numerals[value]

    @staticmethod
    def _clarification_questions(candidate: SearchIntentCandidate) -> list[str]:
        questions: list[str] = []
        if not candidate.disease:
            questions.append("是否需要限定疾病或人群？")
        if not candidate.date_range:
            questions.append("需要限定发表时间范围吗？")
        if not candidate.study_types:
            questions.append("需要限定研究类型（如临床试验、综述或机制研究）吗？")
        return questions
