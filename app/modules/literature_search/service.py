"""Literature-search intent orchestration."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage
from app.integrations.ollama.client import OllamaClient
from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.literature_search.bibtex import to_bibtex
from app.modules.literature_search.model import (
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.literature_search.prompts import PROMPT_VERSION, build_candidate_prompt
from app.modules.literature_search.pubmed_executor import PubMedExecutor
from app.modules.literature_search.query_model import SearchIntentCandidate, relative_year_range
from app.modules.literature_search.repository import LiteratureSearchRepository
from app.modules.literature_search.schema import (
    BooleanQueryResult,
    CitationItem,
    ExpandTermsResponse,
    LiteratureSearchResultRead,
    LiteratureSearchTaskCreate,
    LiteratureSearchTaskList,
    LiteratureSearchTaskRead,
    LiteratureSearchTaskRerun,
    LiteratureSearchTaskVersion,
    MeshCandidate,
    ParseQueryResponse,
    SearchResultChange,
    SearchStrategyExport,
    SearchTaskStatus,
    SearchTermGroup,
    SearchExecuteRequest,
)
from app.modules.literature_search.mesh_client import MeshClient
from app.modules.literature_search.query_builder import build_boolean_query
from app.modules.literature_search.term_expansion import expand_term, is_ascii_search_term

CandidateExtractor = Callable[[str], Awaitable[str]]

# 任务状态机取值：pending → running → succeeded / failed。
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

# 合法状态集合：与 schema.SearchTaskStatus（Literal）保持一致。
_VALID_STATUSES = frozenset({STATUS_PENDING, STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED})


def _coerce_status(value: str) -> SearchTaskStatus:
    """把数据库读取的 str 状态收敛为 SearchTaskStatus Literal。

    设计说明：DB 列声明为 str（SQLite 无枚举），但响应模型要求 Literal；
    运行时校验一次保证只有合法状态能进入响应层，杜绝脏数据外泄。
    """
    if value not in _VALID_STATUSES:
        raise ValueError(f"invalid task status: {value!r}")
    return value  # type: ignore[return-value]  # 已用集合校验收敛为合法 Literal


class LiteratureSearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        candidate_extractor: CandidateExtractor | None = None,
        mesh_client: MeshClient | None = None,
        pubmed_executor: PubMedExecutor | None = None,
    ):
        self.repo = LiteratureSearchRepository(session)
        self.candidate_extractor = candidate_extractor or self._extract_with_configured_model
        self.mesh_client = mesh_client or MeshClient()
        self.pubmed_executor = pubmed_executor or PubMedExecutor(PubMedClient.from_settings())

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
            raw_json = await self.candidate_extractor(build_candidate_prompt(normalized))
            candidate = self._constrain_candidate(
                SearchIntentCandidate.model_validate_json(raw_json), normalized
            )
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
            terms = list(dict.fromkeys([*expansion.synonyms, *user_edits.get(name, [])]))
            ascii_terms = [term for term in terms if is_ascii_search_term(term)]
            if len(ascii_terms) != len(terms):
                warnings.append(f"{name}: Chinese-only terms were retained for editing but omitted from PubMed query output.")
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
            except Exception:
                warnings.append(f"{name}: official MeSH lookup was unavailable; no MeSH candidate was assumed.")
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

    async def create_task(self, request: LiteratureSearchTaskCreate) -> LiteratureSearchTaskRead:
        """创建检索任务并立即执行（pending → running → succeeded/failed）。

        设计说明：任务持久化的是完整检索输入快照，执行复用 WP03.5 的
        pubmed_executor（ESearch + EFetch + verified 打标），不新建平行执行逻辑。
        结果引用落到 LiteratureSearchResult，任务只保存结果 id，避免复制
        items_json 造成历史膨胀。
        """
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
            status=STATUS_PENDING,
            created_at=now,
        )
        saved = await self.repo.create_task(entity)
        await self._run_task(saved, request.retmax)
        return await self.get_task(saved.id)

    async def get_task(self, id: int) -> LiteratureSearchTaskRead:
        """返回任务详情，含按版本升序排列的结果版本时间线。"""
        entity = await self.repo.get_task(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        return await self._to_task_read(entity)

    async def list_tasks(self, offset: int = 0, limit: int = 20) -> LiteratureSearchTaskList:
        """分页返回任务历史（创建时间倒序），列表不携带条目明细。"""
        tasks, total = await self.repo.list_tasks(offset=offset, limit=limit)
        items = [await self._to_task_read(task) for task in tasks]
        return LiteratureSearchTaskList(total=total, offset=offset, limit=limit, items=items)

    async def rerun_task(self, id: int) -> LiteratureSearchTaskRerun:
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
        await self._run_task(entity, entity.retmax)
        updated = await self.repo.get_task(id)
        new_version = await self.repo.get_latest_version(id)
        if updated is None:
            raise NotFoundError(f"LiteratureSearchTask not found: {id}")
        change = None
        if previous is not None and new_version is not None and new_version.id != previous.id:
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
        items = [CitationItem.model_validate(item) for item in json.loads(entity.items_json)]
        return {item.pmid for item in items}

    async def _to_task_read(self, entity: LiteratureSearchTask) -> LiteratureSearchTaskRead:
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
                    change=await self._build_change(prev_ref, ref) if prev_ref is not None else None,
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
            versions=version_reads,
        )

    async def execute_search(self, request: SearchExecuteRequest) -> LiteratureSearchResultRead:
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
            items_json=json.dumps([item.model_dump() for item in items], ensure_ascii=False),
        )
        saved = await self.repo.create_result(entity)
        return self._to_result_read(saved, items)

    async def get_result(self, id: int) -> LiteratureSearchResultRead:
        entity = await self.repo.get_result(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {id}")
        return self._to_result_read(entity)

    async def bibtex(self, id: int) -> str:
        """导出指定检索结果的 BibTeX 文本。

        条目来自数据库持久化的 items_json（当时检索的真实验证状态），导出不
        重新调用 PubMed，也不补全任何缺失字段。
        """
        entity = await self.repo.get_result(id)
        if entity is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {id}")
        items = [CitationItem.model_validate(item) for item in json.loads(entity.items_json)]
        return to_bibtex(items)

    @staticmethod
    def _to_result_read(
        entity: LiteratureSearchResult,
        items: list[CitationItem] | None = None,
    ) -> LiteratureSearchResultRead:
        if items is None:
            items = [
                CitationItem.model_validate(item) for item in json.loads(entity.items_json)
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
        candidate = SearchIntentCandidate(topic=raw_topic)
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)), relative.group(0)
            )
        return candidate

    @staticmethod
    def _constrain_candidate(candidate: SearchIntentCandidate, raw_topic: str) -> SearchIntentCandidate:
        if not candidate.topic.strip() or len(candidate.topic) > len(raw_topic) * 3:
            candidate.topic = raw_topic
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)), relative.group(0)
            )
        return candidate

    @staticmethod
    def _parse_year_count(value: str) -> int:
        if value.isdigit():
            return int(value)
        numerals = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
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
