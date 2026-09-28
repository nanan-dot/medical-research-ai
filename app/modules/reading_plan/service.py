"""Transactional domain orchestration for persisted reading plans."""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Literal, cast

from sqlalchemy.exc import IntegrityError, OperationalError

from app.common.exceptions import ConflictError, NotFoundError, UnprocessableEntityError
from app.modules.literature_search.journal_metric_matching import match_journal_metric
from app.modules.literature_search.journal_metric_normalization import (
    normalize_journal_name,
)
from app.modules.literature_search.journal_metric_query import summarize_metrics
from app.modules.literature_search.journal_metric_repository import (
    JournalMetricRepository,
)
from app.modules.literature_search.schema import CitationItem
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem
from app.modules.reading_plan.reason import build_reading_reason
from app.modules.reading_plan.repository import ReadingPlanRepository
from app.modules.reading_plan.schema import (
    CandidatePage,
    ManualItemCreate,
    PlanGenerateRequest,
    PlanItemPatch,
    PlanItemRead,
    PromoteCoreRequest,
    ReadingPlanRead,
    ReadingPlanVersionPage,
    ReadingPlanVersionSummary,
    StageRead,
)
from app.modules.reading_plan.selection import (
    STAGES,
    SelectionCandidate,
    select_reading_plan,
)

ALGORITHM_VERSION = "reading-plan-metadata-v2"
FULLTEXT_LIMITATION = "Restricted full text not obtained was not analysed."
_RETRYABLE_OPERATIONAL_MARKERS = (
    "database is locked",
    "database table is locked",
    "deadlock detected",
    "lock wait timeout",
    "could not serialize access",
)


def _is_retryable_operational_error(error: OperationalError) -> bool:
    message = str(error.orig or error).casefold()
    return any(marker in message for marker in _RETRYABLE_OPERATIONAL_MARKERS)


class ReadingPlanService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = ReadingPlanRepository(session)

    @staticmethod
    def _citations(result) -> list[CitationItem]:
        return [CitationItem.model_validate(value) for value in json.loads(result.items_json)]

    async def generate(
        self, result_id: int, request: PlanGenerateRequest, *, previous: ReadingPlan | None = None
    ) -> ReadingPlanRead:
        result = await self.repo.result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        citations = self._citations(result)
        if request.duplicate_mode == "consolidated":
            hidden = await self.repo.hidden_duplicate_pmids(result_id)
            citations = [item for item in citations if item.pmid not in hidden]
        scores = await self.repo.active_scores(result_id)
        intent, _ = await self.repo.generation_context(result_id)
        candidates = [
            SelectionCandidate(
                pmid=item.pmid, position=position, year=item.year,
                publication_types=tuple(item.publication_types),
                has_abstract=item.has_abstract,
                mesh_match_count=len(item.mesh_terms),
                article_score=(
                    scores[item.pmid].priority_score if item.pmid in scores else None
                ),
                cited_by_count=(
                    scores[item.pmid].cited_by_count if item.pmid in scores else None
                ),
            )
            for position, item in enumerate(citations)
        ]
        selected = select_reading_plan(candidates, request.target_core_count)
        protected: dict[str, ReadingPlanItem] = {}
        if previous is not None and request.preserve:
            states = await self.repo.states(result_id)
            protected = {
                item.pmid: item for item in previous.items
                if item.is_locked or item.source == "manual" or item.role == "core"
                or states.get(item.pmid) is not None
                and (states[item.pmid].is_key or states[item.pmid].read_status == "read")
            }
        plan = ReadingPlan(
            result_id=result_id, version=await self.repo.next_version(result_id),
            status="draft", algorithm_version=ALGORITHM_VERSION,
            duplicate_mode=request.duplicate_mode,
            target_core_count=request.target_core_count,
            generation_basis_json=json.dumps({
                "used": ["PubMed snapshot position", "bibliographic metadata", "abstract availability", "MeSH", "PublicationType"],
                "available_if_persisted": ["OpenAlex article metrics", "licensed journal metrics"],
                "not_used": ["unobtained restricted full text", "LLM-generated claims"],
            }),
        )
        stage_types: dict[str, set[str]] = {stage: set() for stage in STAGES}
        for value in selected:
            old = protected.get(value.pmid)
            stage = old.stage if old else value.stage
            role = old.role if old else value.role
            citation = next(item for item in citations if item.pmid == value.pmid)
            # System items are re-explained against the new plan context; manual
            # provenance is retained rather than being presented as system evidence.
            regenerate = old is None or old.source != "manual"
            reason = (json.loads(old.reading_reason_json) if old and not regenerate else build_reading_reason(
                citation, stage=stage, role=role, intent=intent,
                prior_stage_types=stage_types[stage], has_score=citation.pmid in scores,
                manual=bool(old and old.source == "manual"),
            ))
            stage_types[stage].update(citation.publication_types)
            plan.items.append(ReadingPlanItem(
                pmid=value.pmid, stage=stage, role=role,
                stage_order=old.stage_order if old else value.stage_order,
                recommendation_reason=str(reason["narrative"]),
                reading_reason_json=json.dumps(reason, ensure_ascii=False),
                evidence_features_json=old.evidence_features_json if old else json.dumps(value.evidence_features),
                limitations_json=old.limitations_json if old else json.dumps(value.limitations),
                source=old.source if old else "system", is_locked=old.is_locked if old else False,
            ))
        try:
            await self.repo.add(plan)
            await self.repo.archive_active(result_id)
            plan.status = "active"
            plan.activated_at = datetime.now(UTC)
            await self.session.flush()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError("Reading plan generation conflicted; retry the request.") from error
        except OperationalError as error:
            await self.session.rollback()
            if _is_retryable_operational_error(error):
                raise ConflictError(
                    "Reading plan generation conflicted; retry the request."
                ) from error
            raise
        return await self._read(plan)

    async def _refresh_reason(
        self, plan: ReadingPlan, item: ReadingPlanItem
    ) -> None:
        result = await self.repo.result(plan.result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {plan.result_id}")
        citations = {citation.pmid: citation for citation in self._citations(result)}
        citation = citations.get(item.pmid)
        if citation is None:
            raise NotFoundError(f"PMID not found in result snapshot: {item.pmid}")
        scores = await self.repo.active_scores(plan.result_id)
        intent, _ = await self.repo.generation_context(plan.result_id)
        prior_stage_types = {
            publication_type
            for other in plan.items
            if other.pmid != item.pmid and other.stage == item.stage
            if other.pmid in citations
            for publication_type in citations[other.pmid].publication_types
        }
        reason = build_reading_reason(
            citation,
            stage=item.stage,
            role=item.role,
            intent=intent,
            prior_stage_types=prior_stage_types,
            has_score=item.pmid in scores,
            manual=item.source == "manual",
        )
        item.reading_reason_json = json.dumps(reason, ensure_ascii=False)
        item.recommendation_reason = str(reason["narrative"])

    async def list_versions(self, result_id: int, limit: int, offset: int) -> ReadingPlanVersionPage:
        if await self.repo.result(result_id) is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        total, plans = await self.repo.plans(result_id, limit, offset)
        states = await self.repo.states(result_id)
        return ReadingPlanVersionPage(total=total, limit=limit, offset=offset, items=[
            ReadingPlanVersionSummary(
                id=plan.id, version=plan.version, status=cast(Literal["draft", "active", "archived"], plan.status),
                algorithm_version=plan.algorithm_version, generated_at=plan.created_at,
                activated_at=plan.activated_at, target_core_count=plan.target_core_count,
                duplicate_mode=cast(Literal["all", "consolidated"], plan.duplicate_mode),
                total_core_count=sum(item.role == "core" for item in plan.items),
                read_count=sum(item.role == "core" and states.get(item.pmid) is not None and states[item.pmid].read_status == "read" for item in plan.items),
            ) for plan in plans
        ])

    async def active(self, result_id: int) -> ReadingPlanRead:
        plan = await self.repo.active(result_id)
        if plan is None:
            raise NotFoundError(f"Active reading plan not found for result: {result_id}")
        return await self._read(plan)

    async def get(self, result_id: int, plan_id: int) -> ReadingPlanRead:
        return await self._read(await self._owned_plan(result_id, plan_id))

    async def replan(self, result_id: int, plan_id: int, request: PlanGenerateRequest) -> ReadingPlanRead:
        previous = await self._owned_plan(result_id, plan_id)
        return await self.generate(result_id, request, previous=previous)

    async def _owned_plan(self, result_id: int, plan_id: int) -> ReadingPlan:
        plan = await self.repo.plan(plan_id)
        if plan is None or plan.result_id != result_id:
            raise NotFoundError(f"Reading plan not found for result: {result_id}")
        return plan

    async def patch_item(self, result_id: int, plan_id: int, pmid: str, request: PlanItemPatch) -> ReadingPlanRead:
        plan = await self._owned_plan(result_id, plan_id)
        item = next((value for value in plan.items if value.pmid == pmid), None)
        if item is None:
            raise NotFoundError(f"PMID not found in reading plan: {pmid}")
        explanation_changed = False
        for field in ("stage", "role", "stage_order", "is_locked"):
            value = getattr(request, field)
            if value is not None:
                explanation_changed = explanation_changed or (
                    field in {"stage", "role"} and value != getattr(item, field)
                )
                setattr(item, field, value)
        if explanation_changed:
            await self._refresh_reason(plan, item)
        item.updated_at = datetime.now(UTC)
        await self.session.flush()
        return await self._read(plan)

    async def add_manual(self, result_id: int, plan_id: int, request: ManualItemCreate) -> ReadingPlanRead:
        plan = await self._owned_plan(result_id, plan_id)
        result = await self.repo.result(result_id)
        citations = self._citations(result)
        if request.pmid not in {item.pmid for item in citations}:
            raise UnprocessableEntityError(f"PMID {request.pmid} does not belong to result {result_id}")
        existing = next((item for item in plan.items if item.pmid == request.pmid), None)
        if existing is not None:
            # Every snapshot article is already a candidate. Manual addition therefore
            # upgrades that persisted candidate instead of creating a duplicate PMID.
            existing.stage = request.stage
            existing.role = request.role
            existing.source = "manual"
            existing.is_locked = request.is_locked
            await self._refresh_reason(plan, existing)
            existing.updated_at = datetime.now(UTC)
            await self.session.flush()
            return await self._read(plan)
        order = max((item.stage_order for item in plan.items if item.stage == request.stage), default=-1) + 1
        plan.items.append(ReadingPlanItem(
            pmid=request.pmid, stage=request.stage, role=request.role, stage_order=order,
            recommendation_reason="Manually added from the immutable PubMed result snapshot.",
            reading_reason_json=json.dumps({"headline": "人工加入的阅读项", "narrative": "该条目由人工从当前 PubMed 结果快照加入。", "stage_fit": ["人工指定阶段。"], "research_question_matches": [], "incremental_value": ["保留人工选择。"], "evidence_sources": ["人工选择", "PubMed 检索结果快照"], "limitations": ["该条目由人工加入；系统未将人工选择解释为医学证据强度。"], "generation_method": "deterministic", "status": "partial"}, ensure_ascii=False),
            evidence_features_json=json.dumps({"manual_selection": {"status": "available", "value": True}}),
            limitations_json=json.dumps([FULLTEXT_LIMITATION]), source="manual", is_locked=request.is_locked,
        ))
        await self.session.flush()
        return await self._read(plan)

    async def delete_item(self, result_id: int, plan_id: int, pmid: str, force: bool = False) -> ReadingPlanRead:
        plan = await self._owned_plan(result_id, plan_id)
        item = next((value for value in plan.items if value.pmid == pmid), None)
        if item is None:
            raise NotFoundError(f"PMID not found in reading plan: {pmid}")
        state = (await self.repo.states(result_id)).get(pmid)
        if not force and (item.is_locked or item.source == "manual" or (state and (state.is_key or state.read_status == "read"))):
            raise ConflictError("Protected item requires force=true before deletion")
        await self.session.delete(item)
        await self.session.flush()
        plan.items.remove(item)
        return await self._read(plan)

    async def save_order(self, result_id: int, plan_id: int, stage: str, pmids: list[str]) -> ReadingPlanRead:
        if stage not in STAGES:
            raise UnprocessableEntityError(f"Invalid stage: {stage}")
        plan = await self._owned_plan(result_id, plan_id)
        expected = {item.pmid for item in plan.items if item.stage == stage and item.role == "core"}
        if len(pmids) != len(set(pmids)) or set(pmids) != expected:
            raise UnprocessableEntityError("pmids must be the complete, unique core set for this stage")
        by_pmid = {item.pmid: item for item in plan.items}
        for order, pmid in enumerate(pmids):
            by_pmid[pmid].stage_order = order
        await self.session.flush()
        return await self._read(plan)

    async def promote(self, result_id: int, plan_id: int, stage: str, request: PromoteCoreRequest) -> ReadingPlanRead:
        plan = await self._owned_plan(result_id, plan_id)
        item = next((value for value in plan.items if value.pmid == request.pmid and value.stage == stage and value.role == "candidate"), None)
        if item is None:
            raise NotFoundError("Candidate not found in requested stage")
        core = [value for value in plan.items if value.role == "core"]
        if len(core) >= plan.target_core_count and request.strategy is None:
            raise ConflictError("Core is full; choose expand or replace")
        if request.strategy == "expand":
            if plan.target_core_count >= 20:
                raise ConflictError("Core cannot expand beyond 20")
            plan.target_core_count += 1
        if request.strategy == "replace":
            replaced = next((value for value in core if value.pmid == request.replace_pmid), None)
            if replaced is None:
                raise UnprocessableEntityError("replace_pmid is not a core item")
            replaced.role = "candidate"
            await self._refresh_reason(plan, replaced)
        item.role = "core"
        await self._refresh_reason(plan, item)
        await self.session.flush()
        return await self._read(plan)

    async def demote(self, result_id: int, plan_id: int, stage: str, pmid: str) -> ReadingPlanRead:
        plan = await self._owned_plan(result_id, plan_id)
        item = next((value for value in plan.items if value.pmid == pmid and value.stage == stage and value.role == "core"), None)
        if item is None:
            raise NotFoundError("Core item not found in requested stage")
        item.role = "candidate"
        await self._refresh_reason(plan, item)
        await self.session.flush()
        return await self._read(plan)

    async def candidates(self, result_id: int, plan_id: int, stage: str, page: int, page_size: int, search: str | None, year: int | None, publication_type: str | None, jcr_quartile: str | None = None, wos_index: str | None = None, cas_quartile: str | None = None, impact_factor_min: float | None = None) -> CandidatePage:
        plan = await self._owned_plan(result_id, plan_id)
        cards = await self._cards(plan)
        values = [card for card in cards if card.stage == stage and card.role == "candidate"]
        if search:
            term = search.casefold()
            values = [card for card in values if term in " ".join([card.pmid, card.title or "", *card.authors]).casefold()]
        if year is not None:
            values = [card for card in values if card.year == year]
        if publication_type:
            term = publication_type.casefold()
            values = [card for card in values if any(term in value.casefold() for value in card.publication_types)]
        def matches_metric(card: PlanItemRead) -> bool:
            metric = card.journal_metrics
            if jcr_quartile and metric.get("jcr_quartile") != jcr_quartile:
                return False
            indexes = cast(list[str] | None, metric.get("wos_indexes"))
            if wos_index and wos_index not in (indexes or []):
                return False
            if cas_quartile and metric.get("cas_quartile") != cas_quartile:
                return False
            impact = cast(float | None, metric.get("impact_factor"))
            return not (
                impact_factor_min is not None
                and (impact is None or impact < impact_factor_min)
            )
        values = [card for card in values if matches_metric(card)]
        start = (page - 1) * page_size
        return CandidatePage(total=len(values), page=page, page_size=page_size, items=values[start:start + page_size])

    async def export(self, result_id: int, plan_id: int, format: str) -> tuple[str, str]:
        plan = await self._owned_plan(result_id, plan_id)
        cards = await self._cards(plan)
        rows = [card.model_dump(mode="json") for card in cards]
        if format == "json":
            return json.dumps(rows, ensure_ascii=False), "application/json"
        if format != "csv":
            raise UnprocessableEntityError("format must be csv or json")
        output = io.StringIO(newline="")
        fields = ["stage", "role", "stage_order", "pmid", "doi", "title", "authors", "journal", "year", "recommendation_reason", "evidence_features", "limitations"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row["authors"] = "; ".join(row["authors"])
            row["evidence_features"] = json.dumps(row["evidence_features"], ensure_ascii=False)
            row["limitations"] = json.dumps(row["limitations"], ensure_ascii=False)
            writer.writerow(row)
        return "\ufeff" + output.getvalue(), "text/csv; charset=utf-8"

    async def _cards(self, plan: ReadingPlan) -> list[PlanItemRead]:
        result = await self.repo.result(plan.result_id)
        citations = {item.pmid: item for item in self._citations(result)}
        states = await self.repo.states(plan.result_id)
        scores = await self.repo.active_scores(plan.result_id)
        metrics = await self._journal_metrics(list(citations.values()))
        cards: list[PlanItemRead] = []
        for item in sorted(plan.items, key=lambda value: (STAGES.index(value.stage), value.role != "core", value.stage_order, value.pmid)):
            citation = citations[item.pmid]
            state = states.get(item.pmid)
            score = scores.get(item.pmid)
            status: Literal["unread", "read"] = (
                "read" if state and state.read_status == "read" else "unread"
            )
            cards.append(PlanItemRead(
                pmid=item.pmid, doi=citation.doi, title=citation.title, authors=citation.authors,
                journal=citation.journal, year=citation.year, volume=citation.volume, issue=citation.issue, pages=citation.pages, publication_types=citation.publication_types,
                abstract_status="available" if citation.has_abstract else "unavailable",
                journal_metrics=metrics[item.pmid],
                article_score={
                    "status": score.score_status if score else "not_collected",
                    "value": score.priority_score if score else None,
                    "cited_by_count": score.cited_by_count if score else None,
                    "citation_observed_at": score.citation_observed_at if score else None,
                },
                recommendation_reason=item.recommendation_reason,
                reading_reason=json.loads(item.reading_reason_json),
                evidence_features=json.loads(item.evidence_features_json),
                limitations=json.loads(item.limitations_json), read_status=status,
                read_at=state.read_at if state and status == "read" else None,
                is_key=state.is_key if state else False, is_locked=item.is_locked,
                source=cast(Literal["system", "manual"], item.source),
                stage=cast(Literal["overview", "clinical_decision", "primary_evidence", "frontier"], item.stage),
                role=cast(Literal["core", "candidate"], item.role),
                stage_order=item.stage_order, pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{item.pmid}/",
            ))
        return cards

    async def _journal_metrics(self, citations: list[CitationItem]) -> dict[str, dict[str, object | None]]:
        repository = JournalMetricRepository(self.session)
        if not await repository.has_active_batches():
            return {item.pmid: {"status": "not_configured", "impact_factor": None, "jcr_quartile": None, "wos_indexes": None, "cas_quartile": None} for item in citations}
        issns = {value for item in citations for value in (item.issn_l, item.issn, item.eissn) if value}
        names = {name for item in citations if (name := normalize_journal_name(item.journal))}
        candidates = await repository.candidates(issns, names)
        output: dict[str, dict[str, object | None]] = {}
        for item in citations:
            match = match_journal_metric(item, candidates)
            if match.status != "matched" or match.journal_key is None or match.method is None:
                output[item.pmid] = {"status": match.status, "impact_factor": None, "jcr_quartile": None, "wos_indexes": None, "cas_quartile": None}
                continue
            summary = summarize_metrics([candidate for candidate in candidates if candidate.journal_key == match.journal_key], match.method)
            latest = summary.latest
            output[item.pmid] = {"status": "matched", "impact_factor": latest.impact_factor.value if latest and latest.impact_factor else None, "jcr_quartile": latest.jcr.best_quartile if latest and latest.jcr else None, "wos_indexes": latest.wos.indexes if latest and latest.wos else None, "cas_quartile": latest.cas.quartile if latest and latest.cas else None}
        return output

    async def _read(self, plan: ReadingPlan) -> ReadingPlanRead:
        cards = await self._cards(plan)
        core = [card for card in cards if card.role == "core"]
        read_count = sum(card.read_status == "read" for card in core)
        stages = [StageRead(
            stage=stage,
            core_count=sum(card.stage == stage and card.role == "core" for card in cards),
            candidate_count=sum(card.stage == stage and card.role == "candidate" for card in cards),
            read_count=sum(card.stage == stage and card.role == "core" and card.read_status == "read" for card in cards),
            core=[card for card in cards if card.stage == stage and card.role == "core"],
        ) for stage in STAGES]
        return ReadingPlanRead(
            id=plan.id, version=plan.version,
            status=cast(Literal["draft", "active", "archived"], plan.status),
            algorithm_version=plan.algorithm_version, result_id=plan.result_id,
            generated_at=plan.created_at, activated_at=plan.activated_at,
            duplicate_mode=cast(Literal["all", "consolidated"], plan.duplicate_mode),
            target_core_count=plan.target_core_count,
            generation_basis=json.loads(plan.generation_basis_json),
            limitations=[FULLTEXT_LIMITATION, "Recommendations use metadata and available abstracts only; they do not assess conclusions or risk of bias from unavailable full text."],
            total_core_count=len(core), read_count=read_count,
            unread_count=len(core) - read_count,
            progress_percent=round(read_count / len(core) * 100, 1) if core else 0.0,
            stages=stages,
        )
