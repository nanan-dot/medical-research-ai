"""Database-backed acceptance coverage for recommendation V5 lifecycle."""

import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.library_item.model import LibraryItem
from app.modules.literature_scoring.model import LiteratureResearchIntentSnapshot
from app.modules.literature_scoring.openalex_client import OpenAlexMetrics
from app.modules.literature_search.model import (
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.literature_search.service import LiteratureSearchService
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem
from app.modules.recommendation.model import RecommendationCandidate
from app.modules.recommendation.reason_generator import NarrativeResult
from app.modules.recommendation.v5_router import router as recommendation_v5_router
from app.modules.recommendation.v5_schema import RecommendationRunCreate
from app.modules.recommendation.v5_service import RecommendationV5Service
from app.modules.research_context.model import ResearchContext


class UnavailableOpenAlex:
    async def metrics_for_pmid(self, pmid: str) -> OpenAlexMetrics:
        return OpenAlexMetrics(None, {}, "unavailable", "openalex_unavailable")


class FakeExecutor:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items
        self.queries: list[str] = []

    async def execute(self, query: str, *, retmax: int):
        self.queries.append(query)
        from app.modules.literature_search.schema import CitationItem

        return [CitationItem.model_validate(item) for item in self.items[:retmax]], len(
            self.items
        )


class FailingExecutor:
    async def execute(self, query: str, *, retmax: int):
        raise RuntimeError("pubmed_unavailable")


class RecordingNarrator:
    def __init__(self) -> None:
        self.calls = 0

    async def render(self, **values: object) -> NarrativeResult:
        self.calls += 1
        return NarrativeResult(
            str(values["fallback_headline"]),
            str(values["fallback_narrative"]),
            None,
        )


def test_all_v5_api_operations_are_registered() -> None:
    operations = {
        (method, route.path)
        for route in recommendation_v5_router.routes
        for method in getattr(route, "methods", set())
    }
    prefix = "/literature-search/{result_id}/recommendations"
    expected = {
        ("POST", f"{prefix}/runs"),
        ("GET", f"{prefix}/status"),
        ("POST", f"{prefix}/cancel"),
        ("GET", f"{prefix}/active"),
        ("GET", f"{prefix}/runs"),
        ("GET", f"{prefix}/runs/{{run_id}}"),
        ("GET", f"{prefix}/runs/{{run_id}}/items/{{pmid}}/explanation"),
        ("POST", f"{prefix}/runs/{{run_id}}/items/{{pmid}}/accept"),
        ("POST", f"{prefix}/runs/{{run_id}}/items/{{pmid}}/dismiss"),
    }
    assert expected <= operations


@pytest.mark.asyncio
async def test_binding_an_unbound_task_preserves_the_context_for_later_intent_use() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="检索研究", description="")
        task = LiteratureSearchTask(
            research_context_id=None,
            original_query="ILD",
            structured_query="{}",
            search_string="ILD[Title/Abstract]",
            database="pubmed",
            result_count=0,
            retmax=20,
            filters="{}",
            model_version="test",
            user_edits="{}",
            status="succeeded",
        )
        session.add_all([context, task])
        await session.flush()

        bound = await LiteratureSearchService(session).bind_task_research_context(
            task.id, context.id
        )

        assert bound.research_context_id == context.id
        assert task.research_context_id == context.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_creating_a_run_binds_a_legacy_unbound_result_to_its_confirmed_intent() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="ILD研究", description="")
        result = LiteratureSearchResult(query="ILD", total_count=0, items_json="[]")
        session.add_all([context, result])
        await session.flush()
        task = LiteratureSearchTask(
            research_context_id=None,
            original_query="ILD",
            structured_query="{}",
            search_string="ILD[Title/Abstract]",
            database="pubmed",
            result_count=0,
            retmax=20,
            filters="{}",
            model_version="test",
            user_edits="{}",
            status="succeeded",
        )
        session.add(task)
        await session.flush()
        session.add(LiteratureSearchResultVersion(task_id=task.id, result_id=result.id, version=1))
        intent = LiteratureResearchIntentSnapshot(
            research_context_id=context.id,
            confirmation_status="user_confirmed",
            dimensions_json='{"disease":["ILD"]}',
            fingerprint="legacy-intent",
        )
        session.add(intent)
        await session.commit()

        created = await RecommendationV5Service(session).queue_run(
            result.id, RecommendationRunCreate(intent_snapshot_id=intent.id)
        )

        assert created.operation == "created"
        assert created.intent_snapshot_id == intent.id
        assert task.research_context_id == context.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_bound_run_is_idempotent_and_decision_and_explanation_are_persisted() -> (
    None
):
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="研究", description="")
        session.add(context)
        await session.flush()
        result = LiteratureSearchResult(query="q", total_count=0, items_json="[]")
        session.add(result)
        await session.flush()
        task = LiteratureSearchTask(
            research_context_id=context.id,
            original_query="q",
            structured_query="",
            search_string="q",
            database="pubmed",
            result_count=0,
            retmax=20,
            filters="",
            model_version="test",
            user_edits="",
            status="succeeded",
        )
        session.add(task)
        await session.flush()
        session.add(
            LiteratureSearchResultVersion(
                task_id=task.id, result_id=result.id, version=1
            )
        )
        intent = LiteratureResearchIntentSnapshot(
            research_context_id=context.id,
            confirmation_status="user_confirmed",
            dimensions_json='{"disease":["cancer"]}',
            fingerprint="intent-1",
        )
        session.add(intent)
        await session.commit()

        service = RecommendationV5Service(session)
        first = await service.queue_run(
            result.id, RecommendationRunCreate(intent_snapshot_id=intent.id)
        )
        await session.commit()
        second = await service.queue_run(
            result.id, RecommendationRunCreate(intent_snapshot_id=intent.id)
        )
        assert first.operation == "created"
        assert second.operation == "reused"
        assert first.run_id == second.run_id
        refreshed = await service.queue_run(
            result.id,
            RecommendationRunCreate(intent_snapshot_id=intent.id, force_refresh=True),
        )
        assert refreshed.operation == "created"
        assert refreshed.run_id != first.run_id

        citation = {"pmid": "123", "title": "Cancer trial", "verified": True}
        session.add(
            RecommendationCandidate(
                run_id=first.run_id,
                pmid="123",
                citation_json=json.dumps(citation),
                priority_score=0.8,
                relevance_score=0.8,
                incremental_value_score=1,
                evidence_fit_score=None,
                recency_score=None,
                overlap_status="novel",
                overlap_evidence_json="[]",
                reason_headline="候选",
                reason_narrative="基于持久化证据生成的推荐理由。",
                reason_matches_json="[]",
                reason_incremental_value="不在当前集合",
                evidence_sources_json='["pubmed_title"]',
                limitations_json='[{"code":"evidence_fit_unavailable","message":"信息不足"}]',
                rank=1,
            )
        )
        await session.commit()
        accepted = await service.decide(result.id, first.run_id, "123", "accepted")
        accepted_again = await service.decide(
            result.id, first.run_id, "123", "accepted"
        )
        await session.commit()
        explanation = await service.explanation(result.id, first.run_id, "123")
        assert accepted == accepted_again
        assert explanation.decision.decision == "accepted"
        assert explanation.reason.evidence_sources == ["pubmed_title"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_intent_from_another_context_is_rejected() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        first = ResearchContext(name="一", description="")
        second = ResearchContext(name="二", description="")
        session.add_all([first, second])
        await session.flush()
        result = LiteratureSearchResult(query="q", total_count=0, items_json="[]")
        session.add(result)
        await session.flush()
        task = LiteratureSearchTask(
            research_context_id=first.id,
            original_query="q",
            structured_query="",
            search_string="q",
            database="pubmed",
            result_count=0,
            retmax=20,
            filters="",
            model_version="test",
            user_edits="",
            status="succeeded",
        )
        session.add(task)
        await session.flush()
        session.add(
            LiteratureSearchResultVersion(
                task_id=task.id, result_id=result.id, version=1
            )
        )
        intent = LiteratureResearchIntentSnapshot(
            research_context_id=second.id,
            confirmation_status="user_confirmed",
            dimensions_json='{"disease":["x"]}',
            fingerprint="other",
        )
        session.add(intent)
        await session.commit()
        with pytest.raises(Exception) as captured:
            await RecommendationV5Service(session).queue_run(
                result.id, RecommendationRunCreate(intent_snapshot_id=intent.id)
            )
        assert getattr(captured.value, "status_code", None) == 409
    await engine.dispose()


@pytest.mark.asyncio
async def test_exploration_run_uses_real_search_query_without_confirmed_intent() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="探索", description="")
        session.add(context)
        await session.flush()
        result = LiteratureSearchResult(query="pulmonary fibrosis", total_count=0, items_json="[]")
        session.add(result)
        await session.flush()
        task = LiteratureSearchTask(
            research_context_id=context.id,
            original_query="pulmonary fibrosis",
            structured_query="",
            search_string="pulmonary fibrosis",
            database="pubmed",
            result_count=0,
            retmax=20,
            filters="",
            model_version="test",
            user_edits="",
            status="succeeded",
        )
        session.add(task)
        await session.flush()
        session.add(LiteratureSearchResultVersion(task_id=task.id, result_id=result.id, version=1))
        await session.commit()

        narrator = RecordingNarrator()
        service = RecommendationV5Service(
            session,
            openalex=UnavailableOpenAlex(),
            narrator=narrator,  # type: ignore[arg-type]
        )
        query = "pulmonary fibrosis AND nintedanib"
        queued = await service.queue_run(
            result.id,
            RecommendationRunCreate(intent_snapshot_id=None, exploration_query=query),
        )
        await session.commit()
        assert queued.intent_snapshot_id is None
        assert queued.exploration_query == query
        executor = FakeExecutor([
            {"pmid": "explore-1", "title": "Pulmonary fibrosis cohort", "abstract": "Nintedanib was studied.", "has_abstract": True},
            {"pmid": "off-topic", "title": "Within-person reliability of composite scores", "has_abstract": True},
            {"pmid": "partial", "title": "Pulmonary fibrosis case report", "has_abstract": True},
        ])
        await service.run(
            queued.run_id,
            executor,
        )
        page = await service.page(result.id)
        assert page.intent_snapshot_id is None
        assert page.exploration_query == query
        assert page.items[0].pmid == "explore-1"
        assert page.total == 1
        assert page.items[0].relevance_score is not None
        assert "nintedanib" in page.items[0].reason.relevance.lower()
        assert executor.queries == [query]
        assert narrator.calls == 0
        assert (await service.status(result.id)).active.narration_status == "pending"  # type: ignore[union-attr]
        await service.polish_run(queued.run_id)
        assert narrator.calls == 1
        assert (await service.status(result.id)).active.narration_status == "completed"  # type: ignore[union-attr]
        assert any(limit.code == "intent_not_confirmed" for limit in page.items[0].reason.limitations)
        assert (await service.status(result.id)).active is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_run_keeps_covered_out_of_quota_and_failure_or_cancel_preserves_active() -> (
    None
):
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="研究", description="")
        session.add(context)
        await session.flush()
        source = [
            {
                "pmid": "1",
                "title": "Cancer source trial",
                "abstract": "cancer mortality",
                "has_abstract": True,
            }
        ]
        result = LiteratureSearchResult(
            query="q", total_count=1, items_json=json.dumps(source)
        )
        session.add(result)
        await session.flush()
        task = LiteratureSearchTask(
            research_context_id=context.id,
            original_query="q",
            structured_query="",
            search_string="q",
            database="pubmed",
            result_count=1,
            retmax=20,
            filters="",
            model_version="test",
            user_edits="",
            status="succeeded",
        )
        session.add(task)
        await session.flush()
        session.add(
            LiteratureSearchResultVersion(
                task_id=task.id, result_id=result.id, version=1
            )
        )
        intent = LiteratureResearchIntentSnapshot(
            research_context_id=context.id,
            confirmation_status="user_confirmed",
            dimensions_json='{"disease":["cancer"],"outcome":["mortality"],"question_type":"treatment"}',
            fingerprint="run-intent",
        )
        session.add(intent)
        plan = ReadingPlan(
            result_id=result.id,
            version=1,
            status="active",
            algorithm_version="test",
            generation_basis_json="{}",
            duplicate_mode="all",
            target_core_count=1,
        )
        session.add(plan)
        await session.flush()
        session.add(
            ReadingPlanItem(
                plan_id=plan.id,
                pmid="5",
                stage="core",
                role="core",
                stage_order=1,
                recommendation_reason="test",
                evidence_features_json="[]",
                limitations_json="[]",
                source="system",
            )
        )
        session.add(
            LibraryItem(
                pmid="4",
                title="Library cancer study",
                source_search_id=result.id,
                fulltext_status="metadata_only",
                fulltext_status_reason="test",
            )
        )
        await session.commit()
        service = RecommendationV5Service(session, openalex=UnavailableOpenAlex())
        queued = await service.queue_run(
            result.id,
            RecommendationRunCreate(
                intent_snapshot_id=intent.id,
                mode="key_evidence",
                candidate_count=3,
            ),
        )
        await session.commit()
        await service.run(
            queued.run_id,
            FakeExecutor(
                [
                    source[0],
                    {
                        "pmid": "2",
                        "title": "New cancer mortality RCT",
                        "abstract": "cancer mortality",
                        "has_abstract": True,
                        "publication_types": ["Randomized Controlled Trial"],
                    },
                    {
                        "pmid": "3",
                        "title": "Cancer source trial.",
                        "abstract": "cancer mortality",
                        "has_abstract": True,
                    },
                    {
                        "pmid": "4",
                        "title": "Library cancer study",
                        "abstract": "cancer mortality",
                        "has_abstract": True,
                    },
                    {
                        "pmid": "5",
                        "title": "Reading plan cancer study",
                        "abstract": "cancer mortality",
                        "has_abstract": True,
                    },
                    {
                        "pmid": "6",
                        "title": "New cancer mortality observational study",
                        "has_abstract": False,
                    },
                ]
            ),
        )
        active = (await service.status(result.id)).active
        assert active is not None
        assert active.completed_count == 6
        assert active.covered_count == 4
        novel_page = await service.page(result.id)
        assert {item.pmid for item in novel_page.items} == {"2", "6"}
        no_abstract = next(item for item in novel_page.items if item.pmid == "6")
        assert any(
            limit.code == "abstract_unavailable"
            for limit in no_abstract.reason.limitations
        )
        assert any(
            limit.code == "openalex_unavailable"
            for item in novel_page.items
            for limit in item.reason.limitations
        )
        assert active.pubmed_query is not None
        assert active.pubmed_total_count == 6
        assert active.incremental_baseline is not None
        assert "novel_candidates_below_requested_count" in active.warnings

        failed = await service.queue_run(
            result.id,
            RecommendationRunCreate(
                intent_snapshot_id=intent.id, mode="latest", candidate_count=2
            ),
        )
        await session.commit()
        await service.run(failed.run_id, FailingExecutor())
        status_after_failure = await service.status(result.id)
        assert status_after_failure.active is not None
        assert status_after_failure.active.run_id == queued.run_id
        failed_history = await service.list_runs(result.id)
        failed_read = next(row for row in failed_history if row.run_id == failed.run_id)
        assert failed_read.last_error is not None
        assert failed_read.last_error.code == "candidate_collection_failed"

        retried = await service.queue_run(
            result.id,
            RecommendationRunCreate(
                intent_snapshot_id=intent.id,
                mode="latest",
                candidate_count=2,
                retry_failed=True,
            ),
        )
        await session.commit()
        assert retried.operation == "created"
        assert retried.run_id != failed.run_id
        retried_again = await service.queue_run(
            result.id,
            RecommendationRunCreate(
                intent_snapshot_id=intent.id,
                mode="latest",
                candidate_count=2,
                retry_failed=True,
            ),
        )
        assert retried_again.operation == "reused"
        assert retried_again.run_id == retried.run_id
        await service.cancel(result.id)
        await session.commit()

        cancellable = await service.queue_run(
            result.id,
            RecommendationRunCreate(
                intent_snapshot_id=intent.id, mode="balanced", candidate_count=3
            ),
        )
        await session.commit()
        cancelled = await service.cancel(result.id)
        await session.commit()
        assert cancelled.run_id == cancellable.run_id
        assert cancelled.status == "cancelled"
        assert (await service.status(result.id)).active.run_id == queued.run_id  # type: ignore[union-attr]
    await engine.dispose()
