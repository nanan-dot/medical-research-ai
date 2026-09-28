"""Acceptance-style API tests for the persisted reading-plan workflow."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.literature_search.model import LiteratureSearchResult


@pytest.fixture
async def client(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'plan.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    items = [
        {"pmid": str(30_000_000 + index), "title": f"Paper {index}", "authors": [f"Author {index}"], "year": 2026 - index % 5, "has_abstract": True, "publication_types": [kind], "mesh_terms": ["medicine"]}
        for index, kind in enumerate(["Systematic Review", "Practice Guideline", "Randomized Controlled Trial", "Journal Article"] * 6)
    ]
    async with factory() as session:
        session.add(LiteratureSearchResult(query="test", total_count=len(items), items_json=json.dumps(items)))
        await session.commit()
    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_ac_rp_02_target_bounds_api(client) -> None:
    assert client.post("/api/v1/literature-search/results/1/reading-plans", json={"target_core_count": 9}).status_code == 422
    assert client.post("/api/v1/literature-search/results/1/reading-plans", json={"target_core_count": 21}).status_code == 422


def test_ac_rp_08_active_plan_contract(client) -> None:
    created = client.post("/api/v1/literature-search/results/1/reading-plans", json={})
    assert created.status_code == 201
    active = client.get("/api/v1/literature-search/results/1/reading-plans/active")
    assert active.status_code == 200
    body = active.json()
    assert body["total_core_count"] == 12
    assert [stage["stage"] for stage in body["stages"]] == ["overview", "clinical_decision", "primary_evidence", "frontier"]
    assert "Restricted full text" in " ".join(body["limitations"])
    card = next(card for stage in body["stages"] for card in stage["core"])
    for field in (
        "pmid", "doi", "title", "authors", "journal", "year",
        "publication_types", "abstract_status", "journal_metrics",
        "article_score", "recommendation_reason", "evidence_features",
        "limitations", "read_status", "read_at", "is_key", "is_locked",
        "source", "pubmed_url",
    ):
        assert field in card
    assert card["journal_metrics"]["status"] == "not_configured"
    assert card["article_score"]["status"] == "not_collected"


def test_ac_rp_09_read_status_controls_read_at(client) -> None:
    assert client.patch("/api/v1/literature-search/1/items/30000000/state", json={"read_status": "read"}).json()["read_at"]
    assert client.patch("/api/v1/literature-search/1/items/30000000/state", json={"read_status": "unread"}).json()["read_at"] is None


def test_ac_rp_10_and_20_manual_item_membership_and_errors(client) -> None:
    plan = client.post("/api/v1/literature-search/results/1/reading-plans", json={}).json()
    assert client.post(f"/api/v1/literature-search/results/1/reading-plans/{plan['id']}/items", json={"pmid": "999"}).status_code == 422
    added = client.post(f"/api/v1/literature-search/results/1/reading-plans/{plan['id']}/items", json={"pmid": "30000000"})
    assert added.status_code == 201


def test_ac_rp_11_and_12_strict_order_and_full_core_conflict(client) -> None:
    plan = client.post("/api/v1/literature-search/results/1/reading-plans", json={}).json()
    stage = next(stage for stage in plan["stages"] if stage["core"])
    bad = client.put(f"/api/v1/literature-search/results/1/reading-plans/{plan['id']}/stages/{stage['stage']}/order", json={"pmids": [stage['core'][0]['pmid']] * len(stage['core'])})
    assert bad.status_code == 422
    candidate_stage = next(stage for stage in plan["stages"] if stage["candidate_count"])
    candidate = client.get(f"/api/v1/literature-search/results/1/reading-plans/{plan['id']}/stages/{candidate_stage['stage']}/candidates").json()["items"][0]
    assert client.post(f"/api/v1/literature-search/results/1/reading-plans/{plan['id']}/stages/{candidate_stage['stage']}/core", json={"pmid": candidate["pmid"]}).status_code == 409


def test_ac_rp_14_and_18_replan_versions_and_export(client) -> None:
    first = client.post("/api/v1/literature-search/results/1/reading-plans", json={}).json()
    second = client.post(f"/api/v1/literature-search/results/1/reading-plans/{first['id']}/replan", json={}).json()
    assert second["version"] == 2
    assert client.get(f"/api/v1/literature-search/results/1/reading-plans/{first['id']}").status_code == 200
    exported_json = client.get(f"/api/v1/literature-search/results/1/reading-plans/{second['id']}/export?format=json")
    assert exported_json.status_code == 200
    assert exported_json.json()[0]["pmid"]
    exported_csv = client.get(f"/api/v1/literature-search/results/1/reading-plans/{second['id']}/export?format=csv")
    assert exported_csv.status_code == 200
    assert "stage,role,stage_order,pmid" in exported_csv.text
    assert "recommendation_reason" in exported_csv.text
    assert client.get(f"/api/v1/literature-search/results/1/reading-plans/{second['id']}/export?format=pdf").status_code == 422


def test_ac_rp_19_legacy_reading_order_is_available_and_deprecated(client) -> None:
    legacy = client.post(
        "/api/v1/literature-search/1/reading-order", json={"manual_order": []}
    )
    assert legacy.status_code == 200
    assert client.get("/openapi.json").json()["paths"][
        "/api/v1/literature-search/{id}/reading-order"
    ]["post"]["deprecated"] is True
