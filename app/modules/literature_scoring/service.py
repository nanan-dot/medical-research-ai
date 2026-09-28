"""Scoring orchestration without hidden GET-side effects or provider calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.literature_scoring.model import (
    LiteratureArticleScore,
    LiteratureResearchIntentSnapshot,
    LiteratureScoreGeneration,
)
from app.modules.literature_scoring.openalex_client import OpenAlexClient
from app.modules.literature_scoring.repository import LiteratureScoringRepository
from app.modules.literature_scoring.schema import (
    ResearchIntentSnapshotCreate,
    ScoreExplanationRead,
    ScoringRunCreate,
    ScoringRunRead,
    ScoringRunStatus,
    ScoringStatusRead,
)
from app.modules.literature_scoring.scoring import popularity_from_yearly_counts
from app.modules.literature_search.repository import LiteratureSearchRepository
from app.modules.literature_search.schema import CitationItem

logger = logging.getLogger(__name__)


class IntentConfirmationRequiredError(ConflictError):
    """Machine-readable guard used until an intent snapshot is confirmed."""

    code = "INTENT_CONFIRMATION_REQUIRED"


class LiteratureScoringService:
    """Own scoring lifecycle; it does not mutate PubMed search snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.results = LiteratureSearchRepository(session)
        self.generations = LiteratureScoringRepository(session)
        self.openalex = OpenAlexClient()

    @staticmethod
    def _fingerprint(result_id: int, request: ScoringRunCreate) -> str:
        payload = {
            "result_id": result_id,
            "intent_snapshot_id": request.intent_snapshot_id,
            "algorithm_version": request.algorithm_version,
            "include_external_metrics": request.include_external_metrics,
            "include_pico": request.include_pico,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    async def create_run(
        self, result_id: int, request: ScoringRunCreate
    ) -> ScoringRunRead:
        result = await self.results.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        intent = await self.generations.get_confirmed_intent(request.intent_snapshot_id)
        if intent is None:
            raise IntentConfirmationRequiredError("请先确认研究问题后再生成正式评分")
        fingerprint = self._fingerprint(result_id, request)
        existing = await self.generations.get_generation_by_fingerprint(
            result_id, fingerprint
        )
        if existing is not None and not request.force_refresh:
            return ScoringRunRead(
                generation_id=existing.id,
                status=cast(ScoringRunStatus, existing.status),
                algorithm_version=existing.algorithm_version,
                operation="reused",
            )
        if request.force_refresh:
            fingerprint = hashlib.sha256(
                f"{fingerprint}:{uuid4().hex}".encode()
            ).hexdigest()
        generation = await self.generations.create(
            LiteratureScoreGeneration(
                result_id=result_id,
                intent_snapshot_id=intent.id,
                algorithm_version=request.algorithm_version,
                feature_schema_version="scoring-features-v1",
                input_fingerprint=fingerprint,
                status="collecting_inputs",
                # A result snapshot may represent a bounded PubMed fetch; activation
                # validates the persisted snapshot, never the remote ESearch total.
                expected_count=len(json.loads(result.items_json)),
                started_at=datetime.now(UTC),
            )
        )
        await self._score_snapshot(
            generation,
            result.items_json,
            intent.dimensions_json,
            request.include_external_metrics,
        )
        return ScoringRunRead(
            generation_id=generation.id,
            status=cast(ScoringRunStatus, generation.status),
            algorithm_version=generation.algorithm_version,
            operation="created",
        )

    async def queue_run(
        self, result_id: int, request: ScoringRunCreate
    ) -> ScoringRunRead:
        """Persist a generation first; a separate-session runner does provider work."""
        result = await self.results.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        intent = await self.generations.get_confirmed_intent(request.intent_snapshot_id)
        if intent is None:
            raise IntentConfirmationRequiredError("请先确认研究问题后再生成正式评分")
        fingerprint = self._fingerprint(result_id, request)
        existing = await self.generations.get_generation_by_fingerprint(
            result_id, fingerprint
        )
        if existing is not None and not request.force_refresh:
            return ScoringRunRead(
                generation_id=existing.id,
                status=cast(ScoringRunStatus, existing.status),
                algorithm_version=existing.algorithm_version,
                operation="reused",
            )
        if request.force_refresh:
            fingerprint = hashlib.sha256(
                f"{fingerprint}:{uuid4().hex}".encode()
            ).hexdigest()
        generation = await self.generations.create(
            LiteratureScoreGeneration(
                result_id=result_id,
                intent_snapshot_id=intent.id,
                algorithm_version=request.algorithm_version,
                feature_schema_version="scoring-features-v1",
                input_fingerprint=fingerprint,
                status="queued",
                expected_count=len(json.loads(result.items_json)),
                request_options_json=json.dumps(
                    {
                        "include_external_metrics": request.include_external_metrics,
                        "include_pico": request.include_pico,
                    }
                ),
            )
        )
        return ScoringRunRead(
            generation_id=generation.id,
            status="queued",
            algorithm_version=generation.algorithm_version,
            operation="created",
        )

    async def run_queued_generation(self, generation_id: int) -> None:
        """Run in a scheduler-owned session, preserving the previous active generation."""
        generation = await self.generations.get_generation(generation_id)
        if (
            generation is None
            or generation.status != "queued"
            or generation.cancel_requested
        ):
            return
        result = await self.results.get_result(generation.result_id)
        intent = await self.generations.get_confirmed_intent(
            generation.intent_snapshot_id
        )
        if result is None or intent is None:
            generation.status = "failed"
            generation.last_error = "generation_inputs_unavailable"
            generation.finished_at = datetime.now(UTC)
            await self.session.commit()
            return
        generation.status = "collecting_inputs"
        generation.started_at = datetime.now(UTC)
        await self.session.commit()
        try:
            options = json.loads(generation.request_options_json)
            await self._score_snapshot(
                generation,
                result.items_json,
                intent.dimensions_json,
                bool(options.get("include_external_metrics")),
            )
            await self.session.commit()
        except asyncio.CancelledError:
            # The cancellation endpoint persisted the terminal state before cancelling this task.
            raise
        except Exception:
            logger.exception("Literature scoring generation %s failed", generation_id)
            await self.session.rollback()
            generation = await self.generations.get_generation(generation_id)
            if generation is not None:
                generation.status = "failed"
                generation.last_error = "scoring_execution_failed"
                generation.finished_at = datetime.now(UTC)
                await self.session.commit()

    async def cancel_run(self, result_id: int) -> ScoringRunRead:
        generation = await self.generations.get_building_generation(result_id)
        if generation is None:
            raise ConflictError("当前没有可取消的评分任务")
        generation.cancel_requested = True
        generation.status = "failed"
        generation.last_error = "cancelled_by_user"
        generation.finished_at = datetime.now(UTC)
        return ScoringRunRead(
            generation_id=generation.id,
            status="failed",
            algorithm_version=generation.algorithm_version,
            operation="created",
        )

    async def _score_snapshot(
        self,
        generation: LiteratureScoreGeneration,
        items_json: str,
        dimensions_json: str,
        include_external_metrics: bool,
    ) -> None:
        """Score only local persisted metadata, then activate the complete generation."""
        items = [CitationItem.model_validate(value) for value in json.loads(items_json)]
        dimensions = json.loads(dimensions_json)
        generation.status = "scoring"
        metrics = (
            await self.openalex.metrics_for_pmids([item.pmid for item in items])
            if include_external_metrics
            else [None] * len(items)
        )
        scores = [
            self._score_item(generation.id, item, dimensions, metric)
            for item, metric in zip(items, metrics, strict=True)
        ]
        await self.generations.add_scores(scores)
        generation.completed_count = len(scores)
        generation.status = "validating"
        if len(scores) != generation.expected_count:
            generation.status = "failed"
            generation.last_error = "snapshot_item_count_changed"
            generation.finished_at = datetime.now(UTC)
            return
        # The status update and commit share the request transaction, therefore consumers
        # observe either the previous active generation or this complete one.
        generation.status = "active"
        generation.activated_at = datetime.now(UTC)
        generation.finished_at = generation.activated_at

    @staticmethod
    def _score_item(
        generation_id: int,
        item: CitationItem,
        dimensions: dict[str, str],
        metric: object | None,
    ) -> LiteratureArticleScore:
        text = f"{item.title or ''} {item.abstract or ''}".lower()
        matches = []
        for name, value in dimensions.items():
            terms = {term for term in value.lower().split() if len(term) > 2}
            if not terms:
                continue
            matched = sorted(term for term in terms if term in text)
            matches.append(
                {
                    "dimension": name,
                    "matched_terms": matched,
                    "status": "matched" if matched else "not_mentioned",
                    "source": "pubmed_snapshot_title_abstract",
                    "version": "pubmed_snapshot_v1",
                    "reason": (
                        None
                        if matched
                        else "snapshot_text_does_not_contain_confirmed_terms"
                    ),
                }
            )
        usable = [entry for entry in matches if entry["matched_terms"]]
        mesh_terms = item.mesh_terms
        mesh_matches = [
            term
            for term in mesh_terms
            if any(
                value.lower() in term.lower() for value in dimensions.values() if value
            )
        ]
        relevance = round(100 * len(usable) / len(matches), 2) if matches else None
        limitations = (
            [] if relevance is not None else ["confirmed_intent_has_no_scorable_terms"]
        )
        if not mesh_terms:
            limitations.append("pubmed_mesh_not_present_in_snapshot")
        cited_by_count = getattr(metric, "cited_by_count", None)
        yearly_counts = getattr(metric, "counts_by_year", {})
        metric_status = getattr(metric, "status", "not_collected")
        metric_reason = getattr(metric, "reason", "openalex_not_requested")
        popularity = popularity_from_yearly_counts(
            yearly_counts, datetime.now(UTC).year
        )
        impact = float(cited_by_count) if cited_by_count is not None else None
        classic = (
            round(impact / max(datetime.now(UTC).year - item.year + 1, 1), 2)
            if impact is not None and item.year is not None
            else None
        )
        return LiteratureArticleScore(
            generation_id=generation_id,
            pmid=item.pmid,
            eligibility_status="included",
            relevance_score=relevance,
            relevance_confidence=round(len(usable) / len(matches), 2)
            if matches
            else None,
            priority_score=relevance,
            popularity_score=popularity.score,
            article_impact_score=impact,
            classic_score=classic,
            cited_by_count=cited_by_count,
            citation_observed_at=datetime.now(UTC)
            if cited_by_count is not None
            else None,
            score_status="available" if relevance is not None else "unavailable",
            components_json=json.dumps(
                {
                    "relevance": relevance,
                    "method": "local_lexical_v1",
                    "openalex": {
                        "status": metric_status,
                        "reason": metric_reason,
                        "cited_by_count": cited_by_count,
                        "popularity": popularity.score,
                    },
                }
            ),
            evidence_json=json.dumps(
                [
                    *matches,
                    {
                        "dimension": "mesh",
                        "source": "pubmed_efetch",
                        "version": "nlm_mesh_descriptor_v1",
                        "status": "available" if mesh_terms else "not_collected",
                        "matched_terms": mesh_matches,
                        "terms": mesh_terms,
                        "reason": None if mesh_terms else "snapshot_has_no_mesh_terms",
                    },
                ],
                ensure_ascii=False,
            ),
            limitations_json=json.dumps(limitations),
            citation_metrics_json=json.dumps(
                {
                    "counts_by_year": yearly_counts,
                    "status": metric_status,
                    "reason": metric_reason,
                }
            ),
        )

    async def create_intent(self, request: ResearchIntentSnapshotCreate) -> int:
        normalized = {
            key: " ".join(value.split())
            for key, value in sorted(request.dimensions.items())
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "research_context_id": request.research_context_id,
                    "dimensions": normalized,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = await self.generations.get_intent_by_fingerprint(
            request.research_context_id, fingerprint
        )
        if existing is not None:
            return existing.id
        intent = await self.generations.create_intent(
            LiteratureResearchIntentSnapshot(
                research_context_id=request.research_context_id,
                dimensions_json=json.dumps(
                    normalized, ensure_ascii=False, sort_keys=True
                ),
                confirmation_status=request.confirmation_status,
                fingerprint=fingerprint,
                confirmed_at=datetime.now(UTC)
                if request.confirmation_status == "user_confirmed"
                else None,
            )
        )
        return intent.id

    async def get_status(self, result_id: int) -> ScoringStatusRead:
        result = await self.results.get_result(result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        active = await self.generations.get_active_generation(result_id)
        building = await self.generations.get_building_generation(result_id)
        latest = await self.generations.get_latest_generation(result_id)
        latest_terminal_failure = (
            latest is not None
            and latest.status == "failed"
            and (active is None or latest.id > active.id)
        )
        current = building or (latest if latest_terminal_failure else active) or latest
        if current is None:
            return ScoringStatusRead(
                status="not_started", total=len(json.loads(result.items_json))
            )
        signals = self._status_signals(
            active, await self.generations.get_active_scores(result_id)
        )
        return ScoringStatusRead(
            active_generation_id=active.id if active else None,
            building_generation_id=building.id if building else None,
            status=cast(ScoringRunStatus, current.status),
            completed=current.completed_count,
            total=current.expected_count,
            started_at=current.started_at,
            updated_at=current.finished_at or current.started_at or current.created_at,
            algorithm_version=current.algorithm_version,
            signals=signals,
            last_error=current.last_error,
            can_retry=current.status == "failed",
        )

    @staticmethod
    def _status_signals(
        active: LiteratureScoreGeneration | None,
        scores: dict[str, LiteratureArticleScore],
    ) -> dict[str, str]:
        """Expose only persisted signal availability, never infer unavailable as zero."""
        if active is None:
            return {
                "relevance": "not_started",
                "pico": "not_started",
                "evidence_fit": "not_started",
                "popularity": "not_started",
                "article_impact": "not_started",
                "classic": "not_started",
            }
        citation_statuses = []
        for score in scores.values():
            try:
                citation_statuses.append(
                    json.loads(score.citation_metrics_json).get("status")
                )
            except (TypeError, json.JSONDecodeError):
                citation_statuses.append("unavailable")
        external_state = (
            "ready"
            if any(score.cited_by_count is not None for score in scores.values())
            else "unavailable"
            if "unavailable" in citation_statuses
            else "not_collected"
        )
        return {
            "relevance": "ready",
            "pico": "ready",
            "evidence_fit": "not_started",
            "popularity": (
                "ready"
                if any(score.popularity_score is not None for score in scores.values())
                else external_state
            ),
            "article_impact": external_state,
            "classic": (
                "ready"
                if any(score.classic_score is not None for score in scores.values())
                else external_state
            ),
        }

    async def get_explanation(self, result_id: int, pmid: str) -> ScoreExplanationRead:
        """Return only stored scoring evidence, isolating failures from result browsing."""
        selected = await self.generations.get_active_score(result_id, pmid)
        if selected is None:
            raise NotFoundError("该文献尚无已激活评分依据")
        generation, score = selected
        return ScoreExplanationRead(
            result_id=result_id,
            pmid=pmid,
            generation_id=generation.id,
            algorithm_version=generation.algorithm_version,
            eligibility={"status": score.eligibility_status, "reasons": []},
            components=json.loads(score.components_json),
            evidence=json.loads(score.evidence_json),
            limitations=json.loads(score.limitations_json),
        )
