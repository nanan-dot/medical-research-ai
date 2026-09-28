"""HTTP acceptance tests for the complete result-scoped V5 contract."""

import json

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.modules.literature_scoring.model import LiteratureResearchIntentSnapshot
from app.modules.literature_search.model import (
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)
from app.modules.recommendation.model import RecommendationCandidate, RecommendationRun
from app.modules.recommendation.v5_router import router
from app.modules.research_context.model import ResearchContext


@pytest.mark.asyncio
async def test_http_lifecycle_history_pagination_explanation_and_decisions(
    monkeypatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        context = ResearchContext(name="真实研究", description="")
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
            fingerprint="http-intent",
        )
        unconfirmed = LiteratureResearchIntentSnapshot(
            research_context_id=context.id,
            confirmation_status="draft",
            dimensions_json='{"disease":["cancer"]}',
            fingerprint="draft-intent",
        )
        session.add_all([intent, unconfirmed])
        await session.commit()
        result_id, intent_id, unconfirmed_id = result.id, intent.id, unconfirmed.id

    app = FastAPI()
    app.include_router(router)

    async def override_session():
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        "app.modules.recommendation.v5_router.RecommendationScheduler.schedule",
        lambda run_id: None,
    )
    transport = httpx.ASGITransport(app=app)
    prefix = f"/literature-search/{result_id}/recommendations"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (
            await client.post(
                f"{prefix}/runs",
                json={"intent_snapshot_id": intent_id, "candidate_count": 0},
            )
        ).status_code == 422
        assert (
            await client.post(
                "/literature-search/999/recommendations/runs",
                json={"intent_snapshot_id": intent_id},
            )
        ).status_code == 404
        assert (
            await client.post(
                f"{prefix}/runs", json={"intent_snapshot_id": unconfirmed_id}
            )
        ).status_code == 409

        created = await client.post(
            f"{prefix}/runs",
            json={
                "intent_snapshot_id": intent_id,
                "mode": "balanced",
                "candidate_count": 2,
            },
        )
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        reused = await client.post(
            f"{prefix}/runs",
            json={
                "intent_snapshot_id": intent_id,
                "mode": "balanced",
                "candidate_count": 2,
            },
        )
        assert reused.json()["operation"] == "reused"
        building = await client.get(f"{prefix}/status")
        assert building.json()["building"]["run_id"] == run_id

        async with sessions() as session:
            run = await session.get(RecommendationRun, run_id)
            assert run is not None
            run.status = "active"
            run.completed_count = 1
            run.covered_count = 0
            citation = {"pmid": "10", "title": "Cancer RCT", "verified": True}
            session.add(
                RecommendationCandidate(
                    run_id=run_id,
                    pmid="10",
                    citation_json=json.dumps(citation),
                    priority_score=0.9,
                    relevance_score=0.9,
                    incremental_value_score=1,
                    evidence_fit_score=1,
                    recency_score=None,
                    open_signal_json="{}",
                    overlap_status="novel",
                    overlap_evidence_json="[]",
                    reason_headline="新增候选",
                    reason_narrative="该文献由持久化结构化证据支持，适合作为新增研究候选。",
                    reason_matches_json="[]",
                    reason_incremental_value="不在当前集合",
                    evidence_sources_json='["pubmed_title"]',
                    limitations_json="[]",
                    rank=1,
                )
            )
            await session.commit()

        status = await client.get(f"{prefix}/status")
        assert status.status_code == 200 and status.json()["active"]["run_id"] == run_id
        history = await client.get(f"{prefix}/runs")
        assert history.status_code == 200 and history.json()[0]["run_id"] == run_id
        detail = await client.get(f"{prefix}/runs/{run_id}")
        assert detail.status_code == 200
        page = await client.get(
            f"{prefix}/active", params={"page": 1, "page_size": 1, "overlap": "novel"}
        )
        assert page.status_code == 200
        assert page.json()["research_name"] == "真实研究"
        assert page.json()["items"][0]["pmid"] == "10"
        covered = await client.get(f"{prefix}/active", params={"overlap": "covered"})
        assert covered.status_code == 200 and covered.json()["total"] == 0
        explanation = await client.get(f"{prefix}/runs/{run_id}/items/10/explanation")
        assert explanation.status_code == 200
        accepted = await client.post(f"{prefix}/runs/{run_id}/items/10/accept")
        assert accepted.json()["decision"] == "accepted"
        dismissed = await client.post(
            f"{prefix}/runs/{run_id}/items/10/dismiss", json={"reason": "off_topic"}
        )
        assert dismissed.json() == {
            "decision": "dismissed",
            "dismiss_reason": "off_topic",
        }
        assert (
            await client.get(f"{prefix}/runs/{run_id}/items/404/explanation")
        ).status_code == 404
        assert (
            await client.get(f"{prefix}/active", params={"page_size": 101})
        ).status_code == 422

    await engine.dispose()
