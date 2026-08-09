"""R2-WP06 去重纯函数与可撤销 API 测试；全程使用临时 SQLite。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.literature_search.dedup import (
    DedupRecord,
    find_duplicate_candidates,
    normalize_doi,
    normalize_title,
)
from app.modules.literature_search.schema import CitationItem
from tests.modules.literature_search.test_history import TASK_PAYLOAD, _ScriptedExecutor


def _record(record_id: str, pmid: str, **fields: object) -> DedupRecord:
    return DedupRecord(record_id, CitationItem(pmid=pmid, **fields), (1,))


@pytest.fixture
async def api_client(tmp_path, monkeypatch):
    """隔离数据库与 PubMed 调用，验证决策层不触发外部请求。"""
    from app.modules.literature_search.service import LiteratureSearchService

    executor = _ScriptedExecutor()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'dedup.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    original_init = LiteratureSearchService.__init__

    def patched_init(
        self,
        session,
        *,
        candidate_extractor=None,
        mesh_client=None,
        pubmed_executor=None,
    ):
        original_init(
            self,
            session,
            candidate_extractor=candidate_extractor,
            mesh_client=mesh_client,
            pubmed_executor=executor,
        )

    monkeypatch.setattr(LiteratureSearchService, "__init__", patched_init)
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client, executor
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_normalizers_are_pure_and_handle_doi_prefix_and_title_punctuation():
    assert normalize_doi("HTTPS://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_title("Trial: A & B.") == "trial a and b"


def test_priority_prefers_pmid_over_lower_confidence_title():
    candidates = find_duplicate_candidates(
        [
            _record("1:a", "same", title="Same title"),
            _record("2:b", "same", title="Same title"),
        ]
    )
    assert [
        (candidate.match_method, candidate.confidence) for candidate in candidates
    ] == [("pmid", "clear")]


def test_doi_is_clear_title_is_fuzzy_and_similar_different_papers_do_not_match():
    candidates = find_duplicate_candidates(
        [
            _record("1:a", "a", doi="https://doi.org/10.1/ABC"),
            _record("2:b", "b", doi="10.1/abc"),
            _record("3:c", "c", title="Cancer therapy outcomes"),
            _record("4:d", "d", title="Cancer therapy outcome study"),
        ]
    )
    assert len(candidates) == 1
    assert candidates[0].match_method == "doi"
    assert candidates[0].confidence == "clear"


def test_dedup_api_preserves_sources_and_resolve_then_undo(api_client):
    client, executor = api_client
    executor.enqueue([CitationItem(pmid="900", title="A", doi="10.1/X")], 1)
    first = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    executor.enqueue(
        [CitationItem(pmid="900", title="A", doi="https://doi.org/10.1/x")], 1
    )
    second = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()

    response = client.post(f"/api/v1/literature-search/{first['id']}/deduplicate")
    assert response.status_code == 200
    group = response.json()["items"][0]
    assert group["match_method"] == "pmid"
    assert group["status"] == "auto_merged"
    assert {tuple(member["source_search_ids"]) for member in group["members"]} == {
        (first["id"],),
        (second["id"],),
    }

    merged = client.post(
        f"/api/v1/duplicate-groups/{group['id']}/resolve", json={"action": "merge_all"}
    )
    assert merged.status_code == 200
    assert merged.json()["status"] == "resolved_merged"
    undone = client.post(
        f"/api/v1/duplicate-groups/{group['id']}/resolve", json={"action": "undo"}
    )
    assert undone.status_code == 200
    assert all(
        member["canonical_record_pmid"] is None for member in undone.json()["members"]
    )


def test_fuzzy_group_requires_manual_resolution(api_client):
    client, executor = api_client
    executor.enqueue([CitationItem(pmid="901", title="Trial: A & B.")], 1)
    task = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    executor.enqueue([CitationItem(pmid="902", title="Trial A and B")], 1)
    client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    group = client.post(f"/api/v1/literature-search/{task['id']}/deduplicate").json()[
        "items"
    ][0]
    assert group["match_method"] == "title_normalized"
    assert group["confidence"] == "fuzzy"
    assert group["status"] == "pending_resolution"
