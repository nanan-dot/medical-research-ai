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
    select_canonical_record,
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


def _positioned_record(position: int, pmid: str, **fields: object) -> DedupRecord:
    """按结果内位置构造记录，record_id 使用受控 result:position:pmid 格式。"""
    return DedupRecord(f"10:{position}:{pmid}", CitationItem(pmid=pmid, **fields), (1,))


def test_select_canonical_record_is_deterministic_and_quality_driven():
    canonical = select_canonical_record(
        (
            _positioned_record(0, "p", verified=False),
            _positioned_record(1, "p", verified=True, has_abstract=True, doi="10.1/x"),
            _positioned_record(2, "p", verified=True, has_abstract=True),
        )
    )
    # verified + 摘要 + DOI 的条目胜出，而不是更靠前的条目。
    assert canonical.record_id == "10:1:p"
    # 质量相同时取更靠前的位置，结果稳定可复现。
    stable = select_canonical_record(
        (
            _positioned_record(3, "p", verified=True),
            _positioned_record(4, "p", verified=True),
        )
    )
    assert stable.record_id == "10:3:p"


def test_result_deduplication_isolated_to_the_requested_snapshot(api_client):
    """扫描 A 时，其他结果快照的相同 PMID 不得混入 A 的工作视图。"""
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="same", title="A one"),
            CitationItem(pmid="same", title="A two"),
        ],
        2,
    )
    executor.enqueue(
        [
            CitationItem(pmid="same", title="B one"),
            CitationItem(pmid="same", title="B two"),
        ],
        2,
    )
    first_task = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    second_task = client.post(
        "/api/v1/literature-search",
        json={**TASK_PAYLOAD, "model_version": "search-intent-v2"},
    ).json()

    result_id = first_task["latest_result_id"]
    other_result_id = second_task["latest_result_id"]
    response = client.put(
        f"/api/v1/literature-search/results/{result_id}/deduplication"
    )

    assert response.status_code == 200
    assert response.json()["result_id"] == result_id
    assert response.json()["scanned_count"] == 2
    groups = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()
    assert groups["total"] == 1
    assert {member["result_id"] for member in groups["items"][0]["members"]} == {
        result_id
    }
    assert other_result_id not in {
        member["result_id"] for member in groups["items"][0]["members"]
    }


def test_result_deduplication_uses_stable_unique_record_keys(api_client):
    """同一快照的相同 PMID 仍按原始位置拥有稳定且不同的身份。"""
    client, executor = api_client
    executor.enqueue(
        [CitationItem(pmid="same", title="one"), CitationItem(pmid="same", title="two")],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]

    first = client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    second = client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    groups = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert groups["total"] == 1
    members = groups["items"][0]["members"]
    assert {member["record_key"] for member in members} == {
        f"{result_id}:0:same",
        f"{result_id}:1:same",
    }
    assert {member["position"] for member in members} == {1, 2}


def test_result_group_contract_and_resolution_are_result_scoped(api_client):
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="a", title="Same", authors=["Author A"], year=2024),
            CitationItem(pmid="b", title="Same", authors=["Author A"], year=2024),
        ],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()["latest_result_id"]
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    group = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups",
        params={"status": "pending_resolution"},
    ).json()["items"][0]
    member = group["members"][0]
    assert group["result_id"] == result_id
    assert group["match_explanation"]
    assert member["title"] == "Same"
    assert member["authors"] == ["Author A"]
    assert member["visible_in_consolidated_view"] is True

    merged = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "merge", "canonical_record_key": member["record_key"]},
    )
    assert merged.status_code == 200
    assert merged.json()["group"]["status"] == "resolved_merged"
    invalid = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "merge", "canonical_record_key": "not-a-member"},
    )
    assert invalid.status_code == 422
    undone = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "undo"},
    )
    assert undone.status_code == 200
    undone_group = undone.json()["group"]
    assert undone_group["status"] == "pending_resolution"
    assert undone_group["canonical_record_key"] is None
    for undone_member in undone_group["members"]:
        assert undone_member["canonical_result_id"] is None
        assert undone_member["canonical_record_pmid"] is None
        assert undone_member["is_canonical"] is False
        assert undone_member["visible_in_consolidated_view"] is True

    reloaded_group = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()["items"][0]
    assert reloaded_group["status"] == "pending_resolution"
    assert reloaded_group["canonical_record_key"] is None
    assert all(
        member["is_canonical"] is False
        and member["visible_in_consolidated_view"] is True
        for member in reloaded_group["members"]
    )
    consolidated = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "consolidated"},
    ).json()
    assert consolidated["filtered_total"] == 2
    assert consolidated["hidden_duplicate_count"] == 0


def test_dedup_api_preserves_sources_and_resolve_then_undo(api_client):
    client, executor = api_client
    executor.enqueue([CitationItem(pmid="900", title="A", doi="10.1/X")], 1)
    first = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    executor.enqueue(
        [CitationItem(pmid="900", title="A", doi="https://doi.org/10.1/x")], 1
    )
    second = client.post(
        "/api/v1/literature-search",
        json={**TASK_PAYLOAD, "model_version": "search-intent-v2"},
    ).json()

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
    client.post(
        "/api/v1/literature-search",
        json={**TASK_PAYLOAD, "model_version": "search-intent-v2"},
    )
    group = client.post(f"/api/v1/literature-search/{task['id']}/deduplicate").json()[
        "items"
    ][0]
    assert group["match_method"] == "title_normalized"
    assert group["confidence"] == "fuzzy"
    assert group["status"] == "pending_resolution"


def test_result_dedup_doi_clear_group_collapses_in_consolidated_view(api_client):
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="1", title="A", doi="HTTPS://doi.org/10.1000/ABC"),
            CitationItem(pmid="2", title="A", doi="10.1000/abc"),
            CitationItem(pmid="3", title="B", doi=None),
        ],
        3,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")

    groups = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()
    assert groups["total"] == 1
    group = groups["items"][0]
    assert group["match_method"] == "doi"
    assert group["confidence"] == "clear"
    assert group["status"] == "auto_merged"
    assert group["canonical_record_key"] is not None
    assert group["members"][0]["doi"] is not None

    consolidated = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "consolidated"},
    ).json()
    # DOI 相同的两条折叠为一条规范记录；第三条与折叠结果一起可见。
    assert consolidated["filtered_total"] == 2
    assert consolidated["hidden_duplicate_count"] == 1
    all_view = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "all"},
    ).json()
    assert all_view["filtered_total"] == 3
    assert all_view["hidden_duplicate_count"] == 0


def test_clear_group_undo_restores_system_selected_canonical_record(api_client):
    """clear 组撤销时必须恢复自动归并，而不是沿用人工改选的规范记录。"""
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="manual", title="A", doi="10.1000/same"),
            CitationItem(
                pmid="system",
                title="A",
                doi="10.1000/same",
                verified=True,
                has_abstract=True,
            ),
        ],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    group = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()["items"][0]
    system_canonical = next(
        member for member in group["members"] if member["is_canonical"]
    )
    manual_canonical = next(
        member
        for member in group["members"]
        if member["record_key"] != system_canonical["record_key"]
    )

    merged = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "merge", "canonical_record_key": manual_canonical["record_key"]},
    )
    assert merged.status_code == 200
    assert merged.json()["group"]["canonical_record_key"] == manual_canonical["record_key"]

    undone = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "undo"},
    )
    assert undone.status_code == 200
    assert undone.json()["group"]["status"] == "auto_merged"
    assert (
        undone.json()["group"]["canonical_record_key"]
        == system_canonical["record_key"]
    )
    assert [
        member["record_key"]
        for member in undone.json()["group"]["members"]
        if member["is_canonical"]
    ] == [system_canonical["record_key"]]

    consolidated = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "consolidated"},
    ).json()
    assert consolidated["filtered_total"] == 1
    assert consolidated["items"][0]["item"]["pmid"] == "system"


def test_fuzzy_keep_all_shows_all_and_undo_restores_pending(api_client):
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="a", title="Same", authors=["Author A"], year=2024),
            CitationItem(pmid="b", title="Same", authors=["Author A"], year=2024),
        ],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    group = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()["items"][0]
    assert group["status"] == "pending_resolution"

    kept = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "keep_all"},
    )
    assert kept.status_code == 200
    assert kept.json()["group"]["status"] == "resolved_keep_all"
    consolidated = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "consolidated"},
    ).json()
    # keep_all 的两条都保留，不折叠。
    assert consolidated["filtered_total"] == 2
    assert consolidated["hidden_duplicate_count"] == 0

    undone = client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "undo"},
    )
    assert undone.status_code == 200
    assert undone.json()["group"]["status"] == "pending_resolution"


def test_cross_result_resolution_is_rejected(api_client):
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="a", title="Same", authors=["A"], year=2024),
            CitationItem(pmid="b", title="Same", authors=["A"], year=2024),
        ],
        2,
    )
    executor.enqueue([CitationItem(pmid="x", title="Other")], 1)
    first = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    second = client.post(
        "/api/v1/literature-search",
        json={**TASK_PAYLOAD, "model_version": "search-intent-v2"},
    ).json()["latest_result_id"]
    client.put(f"/api/v1/literature-search/results/{first}/deduplication")
    group = client.get(
        f"/api/v1/literature-search/results/{first}/duplicate-groups"
    ).json()["items"][0]

    rejected = client.post(
        f"/api/v1/literature-search/results/{second}/duplicate-groups/{group['id']}/resolution",
        json={"action": "keep_all"},
    )
    assert rejected.status_code == 404


def test_put_is_idempotent_and_preserves_manual_resolution(api_client):
    client, executor = api_client
    executor.enqueue(
        [
            CitationItem(pmid="a", title="Same", authors=["A"], year=2024),
            CitationItem(pmid="b", title="Same", authors=["A"], year=2024),
        ],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    group = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()["items"][0]
    client.post(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups/{group['id']}/resolution",
        json={"action": "keep_all"},
    )

    again = client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    assert again.status_code == 200
    groups = client.get(
        f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
    ).json()
    assert groups["total"] == 1
    assert groups["items"][0]["status"] == "resolved_keep_all"


def test_get_consolidated_never_creates_scan_state(api_client):
    client, executor = api_client
    executor.enqueue(
        [CitationItem(pmid="same", title="one"), CitationItem(pmid="same", title="two")],
        2,
    )
    result_id = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()[
        "latest_result_id"
    ]
    before = client.get(
        f"/api/v1/literature-search/results/{result_id}/deduplication"
    ).json()
    assert before["has_scan"] is False

    page = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"duplicate_mode": "consolidated"},
    ).json()
    assert page["duplicate_mode"] == "consolidated"
    assert page["filtered_total"] == 2
    assert page["hidden_duplicate_count"] == 0

    after = client.get(
        f"/api/v1/literature-search/results/{result_id}/deduplication"
    ).json()
    assert after["has_scan"] is False
    assert (
        client.get(
            f"/api/v1/literature-search/results/{result_id}/duplicate-groups"
        ).json()["total"]
        == 0
    )
