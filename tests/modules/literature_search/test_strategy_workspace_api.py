"""RED acceptance tests for persisted strategy-workspace contracts.

The test fixture uses an isolated SQLite database and a controlled PubMed transport;
it must never read or mutate the user's local database.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
async def strategy_client(tmp_path: Path):
    """Expose the strategy API against a fresh, isolated database."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'strategy-workspace.db').as_posix()}"
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
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


def test_strategy_draft_persists_and_rejects_stale_revision(strategy_client: TestClient):
    """AC-STRAT-01/02/03/05: draft save is persistent and revision-protected."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={
            "research_question": "ILD patients receiving antifibrotic therapy",
            "intent_mode": "pico",
            "intent": {"disease": "ILD"},
            "query_text": "ILD[tiab] AND antifibrotic[tiab]",
            "limits": {"database": "pubmed"},
        },
    )

    assert created.status_code == 201
    strategy = created.json()
    strategy_id = strategy["id"]
    assert strategy["revision"] == 1

    loaded = strategy_client.get(f"/api/v1/literature-search/strategies/{strategy_id}")
    assert loaded.status_code == 200
    assert loaded.json()["research_question"] == strategy["research_question"]

    updated = strategy_client.patch(
        f"/api/v1/literature-search/strategies/{strategy_id}",
        json={"revision": 1, "query_text": "ILD[tiab] AND nintedanib[tiab]"},
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["validation_state"] == "stale"
    assert updated.json()["count_state"] == "stale"

    conflict = strategy_client.patch(
        f"/api/v1/literature-search/strategies/{strategy_id}",
        json={"revision": 1, "query_text": "outdated"},
    )
    assert conflict.status_code == 409


def test_strategy_create_persists_generated_terms_and_mesh_snapshot(strategy_client: TestClient):
    """AC-R4-05/08/09/10: entry handoff persists the completed generation snapshot."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={
            "research_question": "ILD patients receiving antifibrotic therapy",
            "intent_mode": "pico",
            "intent": {
                "disease": "interstitial lung disease",
                "intervention": "antifibrotic therapy",
                "outcome": "efficacy and safety",
            },
            "limits": {"database": "pubmed"},
            "query_text": "(interstitial lung disease[tiab]) AND (nintedanib[tiab])",
            "terms": [
                {
                    "text": "interstitial lung disease",
                    "concept_group": "disease",
                    "source": "smart_expansion",
                    "field_tag": "Title/Abstract",
                    "relation_type": "synonym",
                },
                {
                    "text": "nintedanib",
                    "concept_group": "intervention",
                    "source": "smart_expansion",
                    "field_tag": "Title/Abstract",
                    "relation_type": "synonym",
                },
            ],
            "mesh_terms": [
                {
                    "descriptor": "Lung Diseases, Interstitial",
                    "mesh_id": "D008410",
                    "concept_group": "disease",
                    "source": "nlm_mesh",
                    "verification_status": "verified",
                }
            ],
        },
    )

    assert created.status_code == 201
    strategy = created.json()
    assert strategy["intent_mode"] == "pico"
    assert [term["text"] for term in strategy["terms"]] == [
        "interstitial lung disease",
        "nintedanib",
    ]
    assert strategy["mesh_terms"][0]["verification_status"] == "verified"

    restored = strategy_client.get(f"/api/v1/literature-search/strategies/{strategy['id']}")
    assert restored.status_code == 200
    assert restored.json()["terms"] == strategy["terms"]
    assert restored.json()["mesh_terms"] == strategy["mesh_terms"]


def test_strategy_terms_preserve_locks_and_versions_are_immutable(strategy_client: TestClient):
    """AC-STRAT-09/10/20/21/22: term mutations and strategy snapshots are distinct."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    )
    strategy_id = created.json()["id"]

    term = strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy_id}/terms",
        json={"text": "interstitial lung disease", "concept_group": "disease", "source": "user_added", "is_locked": True},
    )
    assert term.status_code == 201
    assert term.json()["is_locked"] is True

    remapped = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/terms/remap")
    assert remapped.status_code == 200, remapped.text
    assert any(item["id"] == term.json()["id"] for item in remapped.json()["terms"])

    first_version = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/versions")
    assert first_version.status_code == 201
    duplicate = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/versions")
    assert duplicate.status_code == 200
    assert duplicate.json()["version"] == first_version.json()["version"]


def test_strategy_terms_can_unlock_and_delete(strategy_client: TestClient):
    """AC-STRAT-09: all user term mutations persist through the strategy API."""
    strategy = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "query_text": "ILD[tiab]"},
    ).json()
    term = strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy['id']}/terms",
        json={"text": "nintedanib", "concept_group": "intervention", "source": "user_added", "is_locked": True},
    ).json()

    unlocked = strategy_client.patch(
        f"/api/v1/literature-search/strategies/{strategy['id']}/terms/{term['id']}",
        json={"is_locked": False},
    )
    deleted = strategy_client.delete(
        f"/api/v1/literature-search/strategies/{strategy['id']}/terms/{term['id']}"
    )

    assert unlocked.status_code == 200
    assert unlocked.json()["is_locked"] is False
    assert deleted.status_code == 204
    assert strategy_client.get(f"/api/v1/literature-search/strategies/{strategy['id']}").json()["terms"] == []


def test_strategy_validation_returns_fingerprint_bound_blocking_errors(strategy_client: TestClient):
    """AC-STRAT-15/16: validation is independent and never labels an invalid query ready."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "(ILD[tiab]"},
    )
    strategy_id = created.json()["id"]

    validation = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/validate")

    assert validation.status_code == 200
    payload = validation.json()
    assert payload["is_syntax_valid"] is False
    assert payload["blocking_errors"][0]["code"] == "unbalanced_parentheses"
    assert payload["validated_fingerprint"] == created.json()["fingerprint"]


def test_strategy_validation_rejects_unknown_field_tags(strategy_client: TestClient):
    """AC-STRAT-15/16: query validation checks field tags independently."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[not-a-real-tag]"},
    ).json()

    validation = strategy_client.post(
        f"/api/v1/literature-search/strategies/{created['id']}/validate"
    )

    assert validation.status_code == 200
    assert validation.json()["are_field_tags_valid"] is False
    assert validation.json()["blocking_errors"][0]["code"] == "unsupported_field_tag"


def test_mesh_refresh_distinguishes_verified_and_unavailable(strategy_client: TestClient, monkeypatch):
    """AC-STRAT-12/13/14: MeSH is official evidence and failure is isolated."""
    from app.modules.literature_search.mesh_client import MeshClient

    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    )
    strategy_id = created.json()["id"]
    strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy_id}/terms",
        json={"text": "interstitial lung disease", "concept_group": "disease", "source": "research_question"},
    )

    async def official_lookup(_self, _term):
        return [{"descriptor": "Lung Diseases, Interstitial", "mesh_id": "D008410", "source": "NLM MeSH"}]

    monkeypatch.setattr(MeshClient, "lookup", official_lookup)
    verified = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/mesh/refresh")
    assert verified.status_code == 200
    assert verified.json()["mesh_terms"][0]["verification_status"] == "verified"

    async def unavailable_lookup(_self, _term):
        raise OSError("NLM unavailable")

    monkeypatch.setattr(MeshClient, "lookup", unavailable_lookup)
    unavailable = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/mesh/refresh")
    assert unavailable.status_code == 200
    assert unavailable.json()["mesh_terms"][0]["verification_status"] == "unavailable"


def test_mesh_refresh_marks_missing_official_descriptors_not_found(strategy_client: TestClient, monkeypatch):
    """AC-STRAT-13: an empty official response is not an availability failure."""
    from app.modules.literature_search.mesh_client import MeshClient

    strategy = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "query_text": "ILD[tiab]"},
    ).json()
    strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy['id']}/terms",
        json={"text": "unknown clinical phrase", "concept_group": "disease", "source": "user_added"},
    )

    async def empty_lookup(_self, _term):
        return []

    monkeypatch.setattr(MeshClient, "lookup", empty_lookup)
    refreshed = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy['id']}/mesh/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["mesh_terms"][0]["verification_status"] == "not_found"


def test_mesh_refresh_uses_one_canonical_descriptor_per_intent_group(
    strategy_client: TestClient, monkeypatch
):
    from app.modules.literature_search.mesh_client import MeshClient

    strategy = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={
            "research_question": "间质性肺疾病患者使用抗纤维化药物的疗效",
            "intent": {
                "disease": "间质性肺疾病患者",
                "intervention": "抗纤维化药物",
            },
            "query_text": "ILD[tiab] AND nintedanib[tiab]",
        },
    ).json()
    for text, concept_group in (
        ("interstitial lung disease", "disease"),
        ("ILD", "disease"),
        ("antifibrotic agents", "intervention"),
        ("nintedanib", "intervention"),
    ):
        strategy_client.post(
            f"/api/v1/literature-search/strategies/{strategy['id']}/terms",
            json={"text": text, "concept_group": concept_group, "source": "user_added"},
        )

    looked_up: list[str] = []

    async def official_lookup(_self, descriptor: str):
        looked_up.append(descriptor)
        return [{"descriptor": descriptor, "mesh_id": "D000001", "source": "NLM MeSH"}]

    monkeypatch.setattr(MeshClient, "lookup", official_lookup)

    refreshed = strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy['id']}/mesh/refresh"
    )

    assert refreshed.status_code == 200
    assert looked_up == ["Lung Diseases, Interstitial", "Antifibrotic Agents"]
    assert len(refreshed.json()["mesh_terms"]) == 2


def test_count_uses_current_fingerprint_and_drops_stale_requests(strategy_client: TestClient, monkeypatch):
    """AC-STRAT-17/18/19: count is sourced from PubMed, never an old result snapshot."""
    from app.integrations.pubmed.client import PubMedClient
    from app.integrations.pubmed.schemas import PubMedSearchResult

    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    ).json()

    async def search(_self, query, *, retmax=20, **_kwargs):
        assert query == "ILD[tiab]"
        assert retmax == 1
        return PubMedSearchResult(pmids=[], total_count=37)

    monkeypatch.setattr(PubMedClient, "search", search)
    counted = strategy_client.post(
        f"/api/v1/literature-search/strategies/{created['id']}/count",
        params={"fingerprint": created["fingerprint"]},
    )
    assert counted.status_code == 200
    assert counted.json()["count"] == 37
    assert counted.json()["source"] == "pubmed"

    stale = strategy_client.post(
        f"/api/v1/literature-search/strategies/{created['id']}/count",
        params={"fingerprint": "outdated"},
    )
    assert stale.status_code == 409


def test_count_failure_does_not_return_a_fabricated_zero(strategy_client: TestClient, monkeypatch):
    """AC-STRAT-18: external PubMed errors remain errors rather than fake counts."""
    from app.integrations.pubmed.client import PubMedClient
    from app.integrations.pubmed.exceptions import PubMedConnectionError

    strategy = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "query_text": "ILD[tiab]"},
    ).json()

    async def unavailable_search(_self, *_args, **_kwargs):
        raise PubMedConnectionError("PubMed unavailable")

    monkeypatch.setattr(PubMedClient, "search", unavailable_search)
    response = strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy['id']}/count",
        params={"fingerprint": strategy["fingerprint"]},
    )

    assert response.status_code == 503
    assert "count" not in response.json()
    restored = strategy_client.get(f"/api/v1/literature-search/strategies/{strategy['id']}").json()
    # The request transaction is rolled back with the external error. The
    # persisted state therefore remains retryable/stale rather than pretending
    # that a failed count has a durable terminal value.
    assert restored["count_state"] == "stale"


def test_strategy_versions_compare_immutable_snapshots(strategy_client: TestClient):
    """AC-STRAT-21/23/24: comparison reads immutable strategy versions only."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    ).json()
    strategy_id = created["id"]
    first = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/versions")
    assert first.status_code == 201

    changed = strategy_client.patch(
        f"/api/v1/literature-search/strategies/{strategy_id}",
        json={"revision": created["revision"], "query_text": "ILD[tiab] AND nintedanib[tiab]"},
    ).json()
    second = strategy_client.post(f"/api/v1/literature-search/strategies/{strategy_id}/versions")
    assert second.status_code == 201
    assert second.json()["version"] == 2

    comparison = strategy_client.get(
        f"/api/v1/literature-search/strategies/{strategy_id}/compare",
        params={"from_version": 1, "to_version": 2},
    )
    assert comparison.status_code == 200
    assert comparison.json()["changes"]["query_text"]["to"] == changed["query_text"]


def test_execute_rejects_strategy_with_blocking_query_error(strategy_client: TestClient):
    """AC-STRAT-25: the server blocks execution before PubMed is contacted."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "(ILD[tiab]"},
    ).json()

    response = strategy_client.post(f"/api/v1/literature-search/strategies/{created['id']}/execute")

    assert response.status_code == 400


def test_execute_reuses_existing_literature_task_service(strategy_client: TestClient, monkeypatch):
    """AC-STRAT-26/27: a strategy executes through the existing task/result domain."""
    from app.modules.literature_search.schema import LiteratureSearchTaskCreateResult
    from app.modules.literature_search.service import LiteratureSearchService

    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    ).json()

    async def create_task(_self, request):
        assert request.search_string == "ILD[tiab]"
        return LiteratureSearchTaskCreateResult(
            id=9,
            original_query=request.original_query,
            structured_query=request.structured_query,
            search_string=request.search_string,
            database="pubmed",
            result_count=1,
            retmax=request.retmax,
            filters=request.filters,
            model_version=request.model_version,
            user_edits=request.user_edits,
            status="succeeded",
            created_at=datetime.now(UTC),
            searched_at=datetime.now(UTC),
            latest_result_id=42,
            strategy_fingerprint="task-fingerprint",
            versions=[],
            operation="created",
            new_result_id=42,
        )

    monkeypatch.setattr(LiteratureSearchService, "create_task", create_task)
    response = strategy_client.post(f"/api/v1/literature-search/strategies/{created['id']}/execute")

    assert response.status_code == 200
    assert response.json()["new_result_id"] == 42


def test_patch_fingerprint_retains_existing_term_identity(strategy_client: TestClient):
    """AC-STRAT-08: a query edit must not drop terms from its stale-response guard."""
    created = strategy_client.post(
        "/api/v1/literature-search/strategies",
        json={"research_question": "ILD", "intent_mode": "unstructured", "query_text": "ILD[tiab]"},
    ).json()
    strategy_id = created["id"]
    strategy_client.post(
        f"/api/v1/literature-search/strategies/{strategy_id}/terms",
        json={"text": "nintedanib", "concept_group": "intervention", "source": "user_added"},
    )
    loaded = strategy_client.get(f"/api/v1/literature-search/strategies/{strategy_id}").json()

    updated = strategy_client.patch(
        f"/api/v1/literature-search/strategies/{strategy_id}",
        json={"revision": loaded["revision"], "query_text": "ILD[tiab] AND nintedanib[tiab]"},
    ).json()

    assert updated["fingerprint"] != created["fingerprint"]
