"""Durable recommendation V5 lifecycle and read-only result assembly."""

from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, cast
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library_item.model import LibraryItem
from app.modules.literature_scoring.model import (
    LiteratureResearchIntentSnapshot,
    LiteratureScoreGeneration,
)
from app.modules.literature_scoring.openalex_client import (
    OpenAlexClient,
    OpenAlexMetrics,
)
from app.modules.literature_search.dedup import normalize_title
from app.modules.literature_search.model import (
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.literature_search.schema import CitationItem
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem
from app.modules.recommendation.article_context import study_design_matches
from app.modules.recommendation.exploration import build_exploration_plan
from app.modules.recommendation.external_work import bounded_async_map
from app.modules.recommendation.model import (
    RecommendationCandidate,
    RecommendationDecision,
    RecommendationRun,
)
from app.modules.recommendation.overlap import classify_overlap, normalize_doi
from app.modules.recommendation.reason_generator import RecommendationNarrator
from app.modules.recommendation.reason_pipeline import (
    RecommendationReasonFactPacket,
    compile_fact_packet,
)
from app.modules.recommendation.relevance import score_relevance
from app.modules.recommendation.scoring import (
    ALGORITHM_VERSION,
    FEATURE_SCHEMA_VERSION,
    Mode,
    evidence_fit,
    intent_concept_coverage,
    openalex_signal,
    priority_score,
    recency_score,
    select_ranked_novel_pmids,
    stable_rank,
)
from app.modules.recommendation.v5_errors import classify_run_error
from app.modules.recommendation.v5_query import build_intent_query_variants
from app.modules.recommendation.v5_repository import RecommendationRepository
from app.modules.recommendation.v5_schema import (
    DecisionRead,
    DismissRequest,
    Limitation,
    MatchEvidence,
    OpenSignalRead,
    OverlapEvidence,
    RecommendationItemRead,
    RecommendationPage,
    RecommendationReason,
    RecommendationRunCreate,
    RecommendationRunRead,
    RecommendationStatusRead,
)
from app.modules.research_context.model import ResearchContext

MAX_RECALL = 500
NARRATION_TIMEOUT_SECONDS = 12
NARRATION_CONCURRENCY = 2
NARRATION_LEASE_STALE_AFTER = timedelta(seconds=NARRATION_TIMEOUT_SECONDS + 3)

_DIMENSION_LABELS = {
    "disease": "疾病",
    "intervention": "干预措施",
    "outcome": "结局",
    "population": "人群",
    "study_type": "研究类型",
}
_SCORE_COMPONENT_LABELS = {
    "relevance": "相关度",
    "incremental": "增量价值",
    "evidence_fit": "证据适配",
    "recency": "新近性",
    "open_signal": "开放影响信号",
}
_OVERLAP_LABELS = {"novel": "新增候选", "covered": "当前结果已覆盖"}


class RecommendationExecutor(Protocol):
    async def execute(
        self, query: str, *, retmax: int
    ) -> tuple[list[CitationItem], int]: ...


class OpenAlexProvider(Protocol):
    async def metrics_for_pmid(self, pmid: str) -> OpenAlexMetrics: ...


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_fingerprint(
    *,
    research_context_id: int,
    intent_fingerprint: str,
    result_id: int,
    result_snapshot: str,
    mode: str,
    candidate_count: int,
    algorithm_version: str = ALGORITHM_VERSION,
) -> str:
    payload = _json(
        {
            "research_context_id": research_context_id,
            "intent": intent_fingerprint,
            "result_id": result_id,
            "result_snapshot": hashlib.sha256(result_snapshot.encode()).hexdigest(),
            "mode": mode,
            "candidate_count": candidate_count,
            "algorithm_version": algorithm_version,
        }
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class RecommendationV5Service:
    def __init__(
        self,
        session: AsyncSession,
        *,
        openalex: OpenAlexProvider | None = None,
        narrator: RecommendationNarrator | None = None,
    ) -> None:
        self.session = session
        self.runs = RecommendationRepository(session)
        self.openalex = openalex or OpenAlexClient()
        self.narrator = narrator or RecommendationNarrator()

    async def _binding(
        self, result_id: int, intent_id: int | None
    ) -> tuple[LiteratureSearchResult, LiteratureResearchIntentSnapshot | None, int]:
        result = await self.session.get(LiteratureSearchResult, result_id)
        intent = await self.session.get(LiteratureResearchIntentSnapshot, intent_id) if intent_id else None
        if result is None or (intent_id is not None and intent is None):
            raise HTTPException(404, "result or intent snapshot not found")
        if intent is not None and intent.confirmation_status != "user_confirmed":
            raise HTTPException(409, "intent snapshot is not user confirmed")
        task_result = await self.session.execute(
            select(LiteratureSearchTask)
            .join(
                LiteratureSearchResultVersion,
                LiteratureSearchResultVersion.task_id == LiteratureSearchTask.id,
            )
            .where(
                LiteratureSearchResultVersion.result_id == result_id,
                LiteratureSearchTask.research_context_id == intent.research_context_id if intent else true(),
            )
            .limit(1)
        )
        task = task_result.scalar_one_or_none()
        if task is None and intent is not None:
            unbound_result = await self.session.execute(
                select(LiteratureSearchTask)
                .join(
                    LiteratureSearchResultVersion,
                    LiteratureSearchResultVersion.task_id == LiteratureSearchTask.id,
                )
                .where(
                    LiteratureSearchResultVersion.result_id == result_id,
                    LiteratureSearchTask.research_context_id.is_(None),
                )
                .order_by(LiteratureSearchResultVersion.version.desc())
                .limit(1)
            )
            task = unbound_result.scalar_one_or_none()
            if task is not None:
                # Older search results predate context binding. An explicitly selected,
                # confirmed Intent supplies the missing durable binding for this task.
                task.research_context_id = intent.research_context_id
                await self.session.flush()
        if task is None or task.research_context_id is None:
            raise HTTPException(
                409, "intent snapshot does not belong to the result research context"
            )
        return result, intent, task.research_context_id

    async def queue_run(
        self, result_id: int, request: RecommendationRunCreate
    ) -> RecommendationRunRead:
        result, intent, context_id = await self._binding(
            result_id, request.intent_snapshot_id
        )
        if intent and request.exploration_query is not None:
            raise HTTPException(422, "exploration_query is only valid without an intent")
        exploration_query = (
            request.exploration_query.strip()
            if request.exploration_query is not None
            else result.query
        )
        if not exploration_query:
            raise HTTPException(422, "exploration_query must not be blank")
        resolved_exploration_query = None
        if intent is None:
            task = (await self.session.execute(
                select(LiteratureSearchTask)
                .join(LiteratureSearchResultVersion, LiteratureSearchResultVersion.task_id == LiteratureSearchTask.id)
                .where(LiteratureSearchResultVersion.result_id == result_id)
                .order_by(LiteratureSearchResultVersion.id.desc()).limit(1)
            )).scalar_one_or_none()
            try:
                plan = build_exploration_plan(
                    exploration_query,
                    original_question=task.original_query if task else "",
                    executed_query=result.query if result.query.isascii() else task.search_string if task else "",
                )
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            resolved_exploration_query = plan.query
        fingerprint = input_fingerprint(
            research_context_id=context_id,
            intent_fingerprint=(
                intent.fingerprint if intent else f"explore:{exploration_query}"
            ),
            result_id=result_id,
            result_snapshot=result.items_json,
            mode=request.mode,
            candidate_count=request.candidate_count,
        )
        existing = await self.runs.get_by_fingerprint(result_id, fingerprint)
        active = await self._active(result_id)
        if existing:
            if request.force_refresh:
                latest_attempt = await self.runs.get_latest_attempt(
                    result_id, fingerprint
                )
                previous_id = latest_attempt.id if latest_attempt else existing.id
                fingerprint = hashlib.sha256(
                    f"{fingerprint}:refresh_after:{previous_id}".encode()
                ).hexdigest()
            elif request.retry_failed and existing.status in ("failed", "cancelled"):
                latest_attempt = await self.runs.get_latest_attempt(
                    result_id, fingerprint
                )
                if latest_attempt and latest_attempt.status in (
                    "queued",
                    "running",
                    "active",
                ):
                    return self._run_read(
                        latest_attempt, "reused", active.id if active else None
                    )
                previous_id = latest_attempt.id if latest_attempt else existing.id
                fingerprint = hashlib.sha256(
                    f"{fingerprint}:retry_after:{previous_id}".encode()
                ).hexdigest()
            else:
                return self._run_read(existing, "reused", active.id if active else None)
        score_generation = (
            await self.session.execute(
                select(LiteratureScoreGeneration)
                .where(
                    LiteratureScoreGeneration.result_id == result_id,
                    LiteratureScoreGeneration.status == "active",
                )
                .order_by(LiteratureScoreGeneration.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        run = RecommendationRun(
            research_context_id=context_id,
            source_result_id=result_id,
            intent_snapshot_id=intent.id if intent else None,
            source_score_generation_id=score_generation.id
            if score_generation
            else None,
            mode=request.mode,
            candidate_count=request.candidate_count,
            algorithm_version=ALGORITHM_VERSION,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            input_fingerprint=fingerprint,
            status="queued",
            request_options_json=_json(
                {
                    "recall_limit": min(
                        MAX_RECALL, max(request.candidate_count * 5, len(json.loads(result.items_json)) + request.candidate_count * 5, 50)
                    ),
                    "base_fingerprint": input_fingerprint(
                        research_context_id=context_id,
                        intent_fingerprint=(
                            intent.fingerprint
                            if intent
                            else f"explore:{exploration_query}"
                        ),
                        result_id=result_id,
                        result_snapshot=result.items_json,
                        mode=request.mode,
                        candidate_count=request.candidate_count,
                    ),
                    "exploration_query": exploration_query if not intent else None,
                    "resolved_exploration_query": resolved_exploration_query,
                }
            ),
        )
        self.session.add(run)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            concurrent = await self.runs.get_by_fingerprint(result_id, fingerprint)
            if concurrent is None:
                raise
            active = await self._active(result_id)
            return self._run_read(
                concurrent, "reused", active.id if active else None
            )
        return self._run_read(run, "created", active.id if active else None)

    async def run(self, run_id: int, executor: RecommendationExecutor) -> None:
        if not await self.runs.claim_queued(run_id):
            await self.session.rollback()
            return
        await self.session.commit()
        run = await self.runs.get_run(run_id)
        if run is None:
            return
        stage = "input_decode"
        try:
            intent = await self.session.get(LiteratureResearchIntentSnapshot, run.intent_snapshot_id) if run.intent_snapshot_id else None
            result = await self.session.get(
                LiteratureSearchResult, run.source_result_id
            )
            if result is None:
                raise RuntimeError("recommendation inputs no longer exist")
            options = json.loads(run.request_options_json)
            dimensions = json.loads(intent.dimensions_json) if intent else {}
            query_variants = build_intent_query_variants(dimensions) if intent else []
            exploration_plan = None
            if not intent:
                from app.modules.recommendation.v5_query import AuditableQuery
                exploration_plan = build_exploration_plan(
                    options.get("resolved_exploration_query") or options.get("exploration_query") or result.query
                )
                query_variants = [
                    AuditableQuery(
                        exploration_plan.query, exploration_plan.terms
                    )
                ]
            built = query_variants[0]
            stage = "pubmed_collection"
            items, total = await executor.execute(built.query, retmax=options["recall_limit"])
            executed_queries = [built.query]
            seen_pmids = {item.pmid for item in items}
            for relaxed in query_variants[1:]:
                if len(seen_pmids) >= run.candidate_count:
                    break
                extra_items, _ = await executor.execute(relaxed.query, retmax=options["recall_limit"])
                executed_queries.append(relaxed.query)
                for item in extra_items:
                    if item.pmid not in seen_pmids:
                        items.append(item)
                        seen_pmids.add(item.pmid)
            recall_items: list[CitationItem] = []
            recalled_pmids: set[str] = set()
            for item in items:
                if item.withdrawn or item.pmid in recalled_pmids:
                    continue
                recalled_pmids.add(item.pmid)
                recall_items.append(item)
            run.expected_count = len(recall_items)
            run.completed_count = 0
            run.heartbeat_at = datetime.now(UTC)
            await self.session.commit()
            stage = "openalex_enrichment"
            metrics_by_pmid: dict[str, OpenAlexMetrics] = {}
            if run.mode == "key_evidence":
                metrics = await bounded_async_map(
                    recall_items,
                    lambda item: self.openalex.metrics_for_pmid(item.pmid),
                    limit=8,
                )
                metrics_by_pmid = dict(
                    zip((item.pmid for item in recall_items), metrics, strict=True)
                )
            stage = "candidate_processing"
            source_items = [
                CitationItem.model_validate(raw)
                for raw in json.loads(result.items_json)
            ]
            source_pmids = {item.pmid for item in source_items}
            source_dois = {
                doi for item in source_items if (doi := normalize_doi(item.doi))
            }
            covered_titles = {
                title
                for item in source_items
                if (title := normalize_title(item.title)) is not None
            }
            concept_baseline = intent_concept_coverage(source_items, dimensions)
            source_type_counts: dict[str, int] = {}
            for source_item in source_items:
                for publication_type in source_item.publication_types:
                    normalized_type = publication_type.strip().lower()
                    source_type_counts[normalized_type] = (
                        source_type_counts.get(normalized_type, 0) + 1
                    )
            reading_pmids = set(
                (
                    await self.session.execute(
                        select(ReadingPlanItem.pmid)
                        .join(ReadingPlan)
                        .where(
                            ReadingPlan.result_id == run.source_result_id,
                            ReadingPlan.status == "active",
                        )
                    )
                )
                .scalars()
                .all()
            )
            libraries = (
                await self.session.execute(
                    select(
                        LibraryItem.pmid,
                        LibraryItem.doi,
                        LibraryItem.document_id,
                        LibraryItem.title,
                    )
                )
            ).all()
            library_pmids = {row.pmid for row in libraries}
            library_dois = {doi for row in libraries if (doi := normalize_doi(row.doi))}
            knowledge_pmids = {
                row.pmid for row in libraries if row.document_id is not None
            }
            knowledge_dois = {
                doi
                for row in libraries
                if row.document_id is not None and (doi := normalize_doi(row.doi))
            }
            covered_titles.update(
                title
                for row in libraries
                if (title := normalize_title(row.title)) is not None
            )
            candidates: list[tuple[RecommendationCandidate, int | None]] = []
            excluded_count = 0
            for item in recall_items:
                await self.session.refresh(run, ["cancel_requested"])
                if run.cancel_requested:
                    run.status, run.finished_at = "cancelled", datetime.now(UTC)
                    await self.session.commit()
                    return
                overlap = classify_overlap(
                    pmid=item.pmid,
                    doi=item.doi,
                    source_pmids=source_pmids,
                    source_dois=source_dois,
                    reading_pmids=reading_pmids,
                    library_pmids=library_pmids,
                    library_dois=library_dois,
                    knowledge_pmids=knowledge_pmids,
                    knowledge_dois=knowledge_dois,
                    title=item.title,
                    covered_titles=covered_titles,
                )
                normalized_candidate_title = normalize_title(item.title)
                if normalized_candidate_title:
                    covered_titles.add(normalized_candidate_title)
                relevance, matches, sources = score_relevance(item, dimensions)
                if exploration_plan is not None:
                    eligible, matches = exploration_plan.evaluate(item)
                    if not eligible:
                        excluded_count += 1
                        run.completed_count += 1
                        continue
                    sources = sorted({field for match in matches for field in str(match["field"]).split(",")})
                    relevance = 1.0 if "pubmed_title" in sources else 0.7
                matches.extend(study_design_matches(item))
                question_type = (
                    dimensions.get("question_type")
                    if isinstance(dimensions.get("question_type"), str)
                    else None
                )
                fit, fit_hits = evidence_fit(question_type, item.publication_types)
                matches.append(
                    {
                        "dimension": "evidence_fit",
                        "status": "matched"
                        if fit_hits
                        else "unavailable"
                        if fit is None
                        else "available_no_preferred_design_match",
                        "matched_terms": fit_hits,
                        "source": "evidence_fit_rule_matrix",
                        "field": "pubmed_publication_types",
                        "reason": question_type
                        or "question_type_or_publication_type_unavailable",
                        "version": FEATURE_SCHEMA_VERSION,
                    }
                )
                rare_types = [
                    publication_type
                    for publication_type in item.publication_types
                    if source_type_counts.get(publication_type.strip().lower(), 0) == 0
                ]
                gap_concepts = [
                    str(term)
                    for match in matches
                    if match["status"] == "matched"
                    for term in cast(list[object], match["matched_terms"])
                    if concept_baseline.get(str(match["dimension"]), {}).get(
                        str(term), 0
                    )
                    == 0
                ]
                incremental = (
                    (1.0 if rare_types or gap_concepts else 0.8)
                    if overlap.status == "novel"
                    else 0.0
                )
                recent = recency_score(item.year)
                metric = metrics_by_pmid.get(item.pmid)
                open_signal = openalex_signal(
                    metric.cited_by_count if metric is not None else None
                )
                priority, used = priority_score(
                    cast(Mode, run.mode),
                    relevance=relevance,
                    incremental=incremental,
                    evidence_fit=fit,
                    recency=recent,
                    open_signal=open_signal,
                )
                limitations = [
                    {"code": code, "message": code.replace("_", " ")}
                    for code in overlap.limitations
                ]
                if not item.has_abstract:
                    limitations.append(
                        {
                            "code": "abstract_unavailable",
                            "message": "PubMed未提供摘要，理由仅基于题名、MeSH和文献类型",
                        }
                    )
                if intent is None:
                    limitations.append({"code": "intent_not_confirmed", "message": "探索推荐仅依据当前真实检索式与可用元数据，未使用已确认研究意图。"})
                if fit is None:
                    limitations.append(
                        {
                            "code": "evidence_fit_unavailable",
                            "message": "问题类型或研究设计信息不足",
                        }
                    )
                if metric is not None and metric.status != "available":
                    limitations.append(
                        {
                            "code": metric.reason or "openalex_unavailable",
                            "message": "OpenAlex开放影响信号不可用，核心推荐不受阻断",
                        }
                    )
                headline = (
                    ("新增且与研究意图匹配的候选" if intent else "基于当前检索主题的新增候选")
                    if overlap.status == "novel"
                    else "已被当前研究集合覆盖的相关文献"
                )
                matched_names = (
                    "、".join(
                        _DIMENSION_LABELS.get(str(match["dimension"]), "研究意图")
                        for match in matches
                        if match["status"] == "matched"
                    )
                    or "暂无明确结构化维度命中"
                )
                used_labels = "、".join(_SCORE_COMPONENT_LABELS.get(component, "其他可用组件") for component in used) or "无"
                narrative = f"该文献基于PubMed可核验元数据匹配{matched_names}。研究设计适配证据为{('、'.join(fit_hits) if fit_hits else '信息不足')}；集合比较结果为{_OVERLAP_LABELS.get(overlap.status, '已完成集合比较')}。评分仅使用可用组件：{used_labels}。"
                packet = compile_fact_packet(
                    source_result_id=run.source_result_id,
                    intent_snapshot_id=run.intent_snapshot_id,
                    exploration_query=options.get("exploration_query"),
                    recommendation_mode=run.mode,
                    year=item.year,
                    publication_types=item.publication_types,
                    matches=matches,
                    overlap_status=overlap.status,
                    limitations=limitations,
                    incremental_detail=(
                        "当前结果未覆盖的匹配概念或文献类型：" + "、".join([*gap_concepts, *rare_types])
                        if overlap.status == "novel" and (rare_types or gap_concepts) else None
                    ),
                )
                candidate = RecommendationCandidate(
                    run_id=run.id,
                    pmid=item.pmid,
                    citation_json=item.model_dump_json(),
                    priority_score=priority,
                    relevance_score=relevance,
                    incremental_value_score=incremental,
                    evidence_fit_score=fit,
                    recency_score=recent,
                    overlap_status=overlap.status,
                    overlap_evidence_json=_json(overlap.evidence),
                    reason_headline=headline,
                    reason_narrative=narrative,
                    reason_matches_json=_json(matches),
                    reason_incremental_value=(
                        "不在已核验集合中；补充当前快照未覆盖的概念或研究类型："
                        + "、".join([*gap_concepts, *rare_types])
                        if overlap.status == "novel" and (rare_types or gap_concepts)
                        else "不在当前快照、阅读计划、本地文库或知识库中"
                        if overlap.status == "novel"
                        else None
                    ),
                    evidence_sources_json=_json(
                        sources
                        + (
                            ["pubmed_publication_type"]
                            if item.publication_types
                            else []
                        )
                        + (
                            ["openalex"]
                            if metric and metric.status == "available"
                            else []
                        )
                    ),
                    limitations_json=_json(limitations),
                    base_reason_json=packet.base_reason.model_dump_json(),
                    reason_fact_packet_json=packet.model_dump_json(),
                    display_reason_source="base",
                    narration_status="pending",
                    narration_fingerprint=packet.fingerprint(),
                    rank=0,
                    open_signal_json=_json(
                        {
                            "source": "openalex",
                            "status": metric.status if metric else "not_requested",
                            "cited_by_count": metric.cited_by_count if metric else None,
                            "counts_by_year": metric.counts_by_year if metric else {},
                            "score": open_signal,
                        }
                    ),
                )
                candidates.append((candidate, item.year))
                run.completed_count += 1
                run.heartbeat_at = datetime.now(UTC)
                await self.session.commit()
            novel_pool = [
                row for row in candidates if row[0].overlap_status == "novel"
            ]
            selected_pmids = select_ranked_novel_pmids(
                [
                    (row[0].pmid, row[0].priority_score, row[1])
                    for row in novel_pool
                ],
                candidate_count=run.candidate_count,
            )
            novel_by_pmid = {row[0].pmid: row for row in novel_pool}
            novel = [novel_by_pmid[pmid] for pmid in selected_pmids]
            covered = [row for row in candidates if row[0].overlap_status != "novel"]
            kept = novel + covered
            order = stable_rank(
                [(row[0].pmid, row[0].priority_score, row[1]) for row in kept]
            )
            ranks = {pmid: index + 1 for index, pmid in enumerate(order)}
            for candidate, _ in kept:
                candidate.rank = ranks[candidate.pmid]
                # 自动润色只服务本轮优先条目，其余已覆盖条目立即使用确定性理由。
                if candidate.rank > run.candidate_count:
                    candidate.narration_status = "not_requested"

            await self.session.refresh(run, ["cancel_requested"])
            if run.cancel_requested:
                run.status, run.finished_at = "cancelled", datetime.now(UTC)
                await self.session.commit()
                return
            stage = "activation"
            self.session.add_all([row[0] for row in kept])
            run.covered_count = len(covered)
            options.update(
                {
                    "pubmed_query": " OR ".join(executed_queries),
                    "pubmed_total_count": total,
                    "collected_at": datetime.now(UTC).isoformat(),
                    "query_terms": [term.__dict__ for term in built.terms],
                    "incremental_baseline": {
                        "source_result_count": len(source_items),
                        "publication_type_counts": source_type_counts,
                        "intent_concept_counts": concept_baseline,
                    },
                    "warnings": (["query_relaxed_to_meet_requested_count"] if len(executed_queries) > 1 else []) + (["novel_candidates_below_requested_count"] if len(novel) < run.candidate_count else []),
                    "narration_status": "pending" if kept else "skipped",
                    "excluded_unmatched_count": excluded_count,
                }
            )
            run.request_options_json = _json(options)
            await self.session.execute(
                update(RecommendationRun)
                .where(
                    RecommendationRun.source_result_id == run.source_result_id,
                    RecommendationRun.status == "active",
                )
                .values(status="superseded")
            )
            run.status = "active"
            run.activated_at = run.finished_at = datetime.now(UTC)
            await self.session.commit()
        except Exception as error:  # noqa: BLE001 - boundary persists all worker failures
            await self.session.rollback()
            failed = await self.session.get(RecommendationRun, run_id)
            if failed:
                failed.status, failed.last_error, failed.finished_at = (
                    "failed",
                    _json(classify_run_error(error, stage=stage)),
                    datetime.now(UTC),
                )
                await self.session.commit()
                for loaded in list(self.session.identity_map.values()):
                    with suppress(Exception):
                        await self.session.refresh(loaded)

    async def polish_run(self, run_id: int) -> None:
        """Best-effort wording enhancement after deterministic activation."""
        run = await self.session.get(RecommendationRun, run_id)
        if run is None or run.status != "active":
            return
        options = json.loads(run.request_options_json or "{}")
        if options.get("narration_status") in (
            "completed",
            "completed_with_fallback",
            "skipped",
            "fallback_timeout",
            "fallback_unavailable",
            "fallback_rejected",
        ):
            return
        options["narration_status"] = "running"
        run.request_options_json = _json(options)
        await self.session.commit()

        rows = list(
            (
                await self.session.execute(
                    select(RecommendationCandidate)
                    .where(
                        RecommendationCandidate.run_id == run.id,
                        RecommendationCandidate.narration_status.in_(("pending", "running")),
                    )
                    .order_by(RecommendationCandidate.rank, RecommendationCandidate.pmid)
                    .limit(run.candidate_count)
                )
            )
            .scalars()
            .all()
        )

        @dataclass(frozen=True)
        class ClaimedNarration:
            candidate_id: int
            fingerprint: str
            claim_token: str
            packet: RecommendationReasonFactPacket

        claimed: list[ClaimedNarration] = []
        for candidate in rows:
            if not candidate.reason_fact_packet_json:
                candidate.narration_status = "fallback_rejected"
                candidate.narration_error_code = "narration_packet_missing"
                continue
            packet = RecommendationReasonFactPacket.model_validate_json(
                candidate.reason_fact_packet_json
            )
            fingerprint = candidate.narration_fingerprint or packet.fingerprint()
            claim_token = uuid4().hex
            action, lease = await self.runs.acquire_narration_lease(
                fingerprint,
                claim_token,
                stale_after=NARRATION_LEASE_STALE_AFTER,
            )
            if action == "cached" and lease is not None:
                if lease.polished_reason_json:
                    candidate.polished_reason_json = lease.polished_reason_json
                    candidate.display_reason_source = "polished"
                    candidate.narration_status = "completed"
                    candidate.narration_model = lease.narration_model
                    candidate.polished_at = lease.updated_at
                else:
                    candidate.narration_status = lease.status
                    candidate.narration_error_code = lease.error_code
                continue
            if action == "busy":
                continue
            candidate.narration_status = "running"
            candidate.narration_fingerprint = fingerprint
            claimed.append(
                ClaimedNarration(candidate.id, fingerprint, claim_token, packet)
            )
        await self.session.commit()

        async def narrate(claim: ClaimedNarration) -> tuple[
            ClaimedNarration, str, str | None, str | None, str | None
        ]:
            try:
                render_packet = getattr(self.narrator, "render_packet", None)
                if render_packet is None:
                    # Compatibility for pre-pipeline in-process test adapters.
                    legacy = await self.narrator.render(
                        citation=CitationItem(pmid="compatibility"),
                        intent={}, evidence={}, fallback_headline="", fallback_narrative="",
                    )
                    return claim, "completed", None, None, legacy.limitation
                result = await asyncio.wait_for(
                    render_packet(claim.packet),
                    timeout=NARRATION_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                return claim, "fallback_timeout", None, None, "narration_timeout"
            if result.output is None:
                status = (
                    "fallback_unavailable"
                    if result.error_code in {"narration_unavailable", "narration_timeout"}
                    else "fallback_rejected"
                )
                return claim, status, None, result.model, result.error_code
            return (
                claim,
                "completed",
                result.output.model_dump_json(),
                result.model,
                None,
            )

        outcomes = await bounded_async_map(claimed, narrate, limit=NARRATION_CONCURRENCY)
        for claim, outcome, polished_json, model, error_code in outcomes:
            if not await self.runs.finalize_narration_lease(
                fingerprint=claim.fingerprint,
                claim_token=claim.claim_token,
                status=outcome,
                polished_reason_json=polished_json,
                narration_model=model,
                error_code=error_code,
            ):
                continue
            values: dict[str, object] = {
                "narration_status": outcome,
                "narration_model": model,
                "narration_error_code": error_code,
            }
            if polished_json:
                values.update(
                    {
                        "polished_reason_json": polished_json,
                        "display_reason_source": "polished",
                        "polished_at": datetime.now(UTC),
                    }
                )
            await self.session.execute(
                update(RecommendationCandidate)
                .where(
                    RecommendationCandidate.id == claim.candidate_id,
                    RecommendationCandidate.narration_status == "running",
                    RecommendationCandidate.narration_fingerprint == claim.fingerprint,
                )
                .values(**values)
            )
        run = await self.session.get(RecommendationRun, run_id)
        if run is not None:
            options = json.loads(run.request_options_json or "{}")
            statuses = list(
                (
                    await self.session.execute(
                        select(RecommendationCandidate.narration_status).where(
                            RecommendationCandidate.run_id == run.id
                        )
                    )
                ).scalars()
            )
            options["narration_status"] = self._narration_summary(statuses)
            run.request_options_json = _json(options)
        await self.session.commit()

    @staticmethod
    def _narration_summary(statuses: list[str]) -> str:
        if not statuses:
            return "skipped"
        if "running" in statuses:
            return "running"
        if "pending" in statuses:
            return "pending"
        fallback_statuses = {status for status in statuses if status.startswith("fallback_")}
        if not fallback_statuses:
            return "completed"
        if "completed" in statuses or len(fallback_statuses) > 1:
            return "completed_with_fallback"
        return fallback_statuses.pop()

    async def cancel(self, result_id: int) -> RecommendationRunRead:
        run = (
            await self.session.execute(
                select(RecommendationRun)
                .where(
                    RecommendationRun.source_result_id == result_id,
                    RecommendationRun.status.in_(("queued", "running")),
                )
                .order_by(RecommendationRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if run is None:
            raise HTTPException(409, "no recommendation run can be cancelled")
        run.cancel_requested = True
        run.status, run.finished_at = "cancelled", datetime.now(UTC)
        active = await self._active(result_id)
        return self._run_read(run, "reused", active.id if active else None)

    async def status(self, result_id: int) -> RecommendationStatusRead:
        building = (
            await self.session.execute(
                select(RecommendationRun)
                .where(
                    RecommendationRun.source_result_id == result_id,
                    RecommendationRun.status.in_(("queued", "running")),
                )
                .order_by(RecommendationRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        active = await self._active(result_id)
        latest = (
            await self.session.execute(
                select(RecommendationRun)
                .where(RecommendationRun.source_result_id == result_id)
                .order_by(RecommendationRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return RecommendationStatusRead(
            building=self._run_read(building) if building else None,
            active=self._run_read(active) if active else None,
            can_retry=bool(latest and latest.status in ("failed", "cancelled")),
        )

    async def list_runs(self, result_id: int) -> list[RecommendationRunRead]:
        rows = await self.runs.list_runs(result_id)
        return [self._run_read(row) for row in rows]

    async def get_run(self, result_id: int, run_id: int) -> RecommendationRunRead:
        run = await self.runs.get_run(run_id)
        if run is None or run.source_result_id != result_id:
            raise HTTPException(404, "recommendation run not found")
        return self._run_read(run)

    async def page(
        self,
        result_id: int,
        *,
        run_id: int | None = None,
        overlap: str = "novel",
        page: int = 1,
        page_size: int = 20,
        sort: str = "priority",
    ) -> RecommendationPage:
        run = (
            await self.session.get(RecommendationRun, run_id)
            if run_id
            else await self._active(result_id)
        )
        if run is None or run.source_result_id != result_id:
            raise HTTPException(404, "recommendation run not found")
        context = await self.session.get(ResearchContext, run.research_context_id)
        if context is None:
            raise HTTPException(404, "research context not found")
        predicate = (
            RecommendationCandidate.overlap_status == "novel"
            if overlap == "novel"
            else RecommendationCandidate.overlap_status != "novel"
        )
        order = (
            RecommendationCandidate.rank.asc()
            if sort == "priority"
            else RecommendationCandidate.created_at.desc()
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(RecommendationCandidate)
                    .where(RecommendationCandidate.run_id == run.id, predicate)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    select(RecommendationCandidate)
                    .where(RecommendationCandidate.run_id == run.id, predicate)
                    .order_by(order, RecommendationCandidate.pmid)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        decisions = {
            row.pmid: row
            for row in (
                await self.session.execute(
                    select(RecommendationDecision).where(
                        RecommendationDecision.run_id == run.id
                    )
                )
            )
            .scalars()
            .all()
        }
        novel_count = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(RecommendationCandidate)
                    .where(
                        RecommendationCandidate.run_id == run.id,
                        RecommendationCandidate.overlap_status == "novel",
                    )
                )
            ).scalar_one()
        )
        return RecommendationPage(
            research_context_id=run.research_context_id,
            research_name=context.name,
            source_result_id=run.source_result_id,
            intent_snapshot_id=run.intent_snapshot_id,
            exploration_query=(
                json.loads(run.request_options_json or "{}").get("exploration_query")
            ),
            run_id=run.id,
            mode=cast(Mode, run.mode),
            algorithm_version=run.algorithm_version,
            total=total,
            novel_count=novel_count,
            covered_count=run.covered_count,
            page=page,
            page_size=page_size,
            items=[self._item_read(row, decisions.get(row.pmid)) for row in rows],
        )

    async def decide(
        self,
        result_id: int,
        run_id: int,
        pmid: str,
        decision: str,
        dismiss: DismissRequest | None = None,
    ) -> DecisionRead:
        run = await self.session.get(RecommendationRun, run_id)
        if run is None or run.source_result_id != result_id:
            raise HTTPException(404, "recommendation run not found")
        candidate = (
            await self.session.execute(
                select(RecommendationCandidate).where(
                    RecommendationCandidate.run_id == run_id,
                    RecommendationCandidate.pmid == pmid,
                )
            )
        ).scalar_one_or_none()
        if candidate is None:
            raise HTTPException(404, "recommendation candidate not found")
        row = (
            await self.session.execute(
                select(RecommendationDecision).where(
                    RecommendationDecision.run_id == run_id,
                    RecommendationDecision.pmid == pmid,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = RecommendationDecision(run_id=run_id, pmid=pmid)
            self.session.add(row)
        row.decision = decision
        row.dismiss_reason = dismiss.reason if dismiss else None
        row.updated_at = datetime.now(UTC)
        await self.session.flush()
        return DecisionRead.model_validate(
            {"decision": row.decision, "dismiss_reason": row.dismiss_reason}
        )

    async def explanation(
        self, result_id: int, run_id: int, pmid: str
    ) -> RecommendationItemRead:
        run = await self.session.get(RecommendationRun, run_id)
        if run is None or run.source_result_id != result_id:
            raise HTTPException(404, "recommendation run not found")
        row = (
            await self.session.execute(
                select(RecommendationCandidate).where(
                    RecommendationCandidate.run_id == run_id,
                    RecommendationCandidate.pmid == pmid,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "recommendation candidate not found")
        decision = (
            await self.session.execute(
                select(RecommendationDecision).where(
                    RecommendationDecision.run_id == run_id,
                    RecommendationDecision.pmid == pmid,
                )
            )
        ).scalar_one_or_none()
        return self._item_read(row, decision)

    async def _active(self, result_id: int) -> RecommendationRun | None:
        return await self.runs.get_active(result_id)

    @staticmethod
    def _run_read(
        run: RecommendationRun,
        operation: str = "reused",
        active_run_id: int | None = None,
    ) -> RecommendationRunRead:
        options = json.loads(run.request_options_json or "{}")
        return RecommendationRunRead.model_validate(
            {
                "run_id": run.id,
                "status": run.status,
                "operation": operation,
                "active_run_id": active_run_id,
                "mode": run.mode,
                "candidate_count": run.candidate_count,
                "expected_count": run.expected_count,
                "completed_count": run.completed_count,
                "covered_count": run.covered_count,
                "algorithm_version": run.algorithm_version,
                "feature_schema_version": run.feature_schema_version,
                "intent_snapshot_id": run.intent_snapshot_id,
                "exploration_query": options.get("exploration_query"),
                "narration_status": options.get("narration_status", "not_requested"),
                "source_result_id": run.source_result_id,
                "source_score_generation_id": run.source_score_generation_id,
                "last_error": (
                    json.loads(run.last_error)
                    if run.last_error and run.last_error.startswith("{")
                    else {
                        "code": "recommendation_run_failed",
                        "message": run.last_error,
                    }
                    if run.last_error
                    else None
                ),
                "warnings": options.get("warnings", []) + (["recommendation_quality_upgrade_required"] if run.algorithm_version != ALGORITHM_VERSION else []),
                "pubmed_query": options.get("pubmed_query"),
                "pubmed_total_count": options.get("pubmed_total_count"),
                "collected_at": options.get("collected_at"),
                "query_terms": options.get("query_terms", []),
                "incremental_baseline": options.get("incremental_baseline"),
                "created_at": run.created_at,
                "activated_at": run.activated_at,
            }
        )

    @staticmethod
    def _item_read(
        row: RecommendationCandidate, decision: RecommendationDecision | None
    ) -> RecommendationItemRead:
        headline, relevance, incremental, limitation = (
            row.reason_headline,
            row.reason_narrative,
            row.reason_incremental_value,
            None,
        )
        display_source: Literal["base", "polished"] = "base"
        if row.base_reason_json:
            base = json.loads(row.base_reason_json)
            headline = base["headline"]
            relevance = base["relevance"]
            incremental = base["incremental_value"]
            limitation = base["limitation"]
            narrative = " ".join((relevance, incremental, base["evidence_note"], limitation))
        else:
            narrative = row.reason_narrative
        if row.display_reason_source == "polished" and row.polished_reason_json:
            polished = json.loads(row.polished_reason_json)
            headline = polished["headline"]["text"]
            relevance = polished["relevance"]["text"]
            incremental = polished["incremental_value"]["text"]
            limitation = polished["limitation"]["text"]
            narrative = f"{relevance} {incremental} {limitation}"
            display_source = "polished"
        return RecommendationItemRead(
            pmid=row.pmid,
            citation=CitationItem.model_validate_json(row.citation_json),
            priority_score=row.priority_score,
            relevance_score=row.relevance_score,
            incremental_value_score=row.incremental_value_score,
            evidence_fit_score=row.evidence_fit_score,
            recency_score=row.recency_score,
            overlap_status=row.overlap_status,
            overlap_evidence=[
                OverlapEvidence.model_validate(item)
                for item in json.loads(row.overlap_evidence_json)
            ],
            open_signal=OpenSignalRead.model_validate_json(row.open_signal_json),
            reason=RecommendationReason(
                headline=headline,
                narrative=narrative,
                relevance=relevance,
                matches=[
                    MatchEvidence.model_validate(item)
                    for item in json.loads(row.reason_matches_json)
                ],
                incremental_value=incremental,
                evidence_sources=json.loads(row.evidence_sources_json),
                limitations=[
                    Limitation.model_validate(item)
                    for item in json.loads(row.limitations_json)
                ],
                limitation=limitation,
                display_source=display_source,
            ),
            rank=row.rank,
            decision=DecisionRead.model_validate(
                {
                    "decision": decision.decision if decision else "pending",
                    "dismiss_reason": decision.dismiss_reason if decision else None,
                }
            ),
            narration_status=row.narration_status,
        )
