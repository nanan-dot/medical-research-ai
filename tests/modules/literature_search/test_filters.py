"""literature_search 筛选、排序与分页测试（R2-WP05）。

覆盖验收项：组合筛选、空结果、页码边界、排序稳定、排序理由可解释、
非法筛选参数、用户态（saved/read/tags）写入与筛选联动、自定义排序。

设计说明：单元测试直接调用 filtering / ranking / user_state 纯函数，验证
筛选与排序逻辑；接口测试复用 test_history 的脚本化执行器替身，避免真实网络。
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.literature_search.filtering import apply_filters
from app.modules.literature_search.ranking import sort_items
from app.modules.literature_search.schema import (
    CitationItem,
    ResultQueryParams,
)
from app.modules.literature_search.user_state import (
    DEFAULT_READ_STATUS,
    deserialize_tags,
    normalize_tags,
    serialize_tags,
)

TASK_PAYLOAD = {
    "original_query": "胃癌 EGFR 免疫治疗",
    "structured_query": json.dumps(
        {"topic": "胃癌 EGFR 免疫治疗", "disease": "胃癌"}, ensure_ascii=False
    ),
    "search_string": (
        '"stomach neoplasms"[Title/Abstract] AND "EGFR"[Title/Abstract] '
        "AND immunotherapy"
    ),
    "database": "pubmed",
    "filters": json.dumps({"language": "English"}, ensure_ascii=False),
    "model_version": "search-intent-v1",
    "user_edits": json.dumps(
        {"disease": ["胃癌", "gastric cancer"]}, ensure_ascii=False
    ),
    "retmax": 20,
}


def _item(
    pmid: str,
    year: int = 2024,
    journal: str = "Nature Medicine",
    authors: tuple[str, ...] = ("Kim J",),
    has_abstract: bool = True,
    publication_types: tuple[str, ...] = ("Journal Article",),
) -> CitationItem:
    """构造一条带真实来源验证标记的替身条目（字段可覆盖以驱动筛选）。"""
    return CitationItem(
        pmid=pmid,
        doi=None,
        title=f"Title {pmid}",
        authors=list(authors),
        journal=journal,
        year=year,
        verified=True,
        verified_by="pubmed",
        verified_on="2026-08-05T00:00:00+00:00",
        has_abstract=has_abstract,
        publication_types=list(publication_types),
    )


class _ScriptedExecutor:
    """脚本化替身执行器：按调用顺序返回预置结果。"""

    def __init__(self) -> None:
        self.steps: list[tuple[list[CitationItem], int]] = []
        self.index = 0

    def enqueue(self, items: list[CitationItem], total_count: int) -> None:
        self.steps.append((items, total_count))

    async def execute(self, query: str, *, retmax: int = 20):
        if self.index >= len(self.steps):
            raise AssertionError("executor called more times than scripted steps")
        step = self.steps[self.index]
        self.index += 1
        return step


@pytest.fixture
async def api_client(tmp_path, monkeypatch):
    from app.modules.literature_search.service import LiteratureSearchService

    executor = _ScriptedExecutor()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'filters.db').as_posix()}"
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
        self, session, *, candidate_extractor=None, mesh_client=None, pubmed_executor=None
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


# 单元测试：用户态标签纯函数
# ----------------------------------------------------------------------


def test_normalize_tags_deduplicates_and_trims():
    assert normalize_tags([" cancer ", "Cancer", "", "  "]) == ["cancer", "Cancer"]
    assert normalize_tags(None) == []
    assert normalize_tags(["a" * 80]) == ["a" * 50]
    assert len(normalize_tags([f"t{i}" for i in range(30)])) == 20


def test_serialize_deserialize_tags_roundtrip():
    raw = serialize_tags(["cancer", "immunotherapy"])
    assert deserialize_tags(raw) == ["cancer", "immunotherapy"]
    assert deserialize_tags("not json") == []
    assert deserialize_tags(None) == []
    assert deserialize_tags('{"a": 1}') == []


# 单元测试：筛选逻辑（组合筛选）
# ----------------------------------------------------------------------


def test_apply_filters_combines_snapshot_and_user_state():
    items = [
        _item("1", year=2024, journal="Nature", has_abstract=True),
        _item("2", year=2023, journal="Science", has_abstract=False),
        _item("3", year=2022, journal="Cell", has_abstract=True),
    ]
    states = {
        "1": (True, "read", ["key"]),
        "2": (False, "unread", []),
        "3": (True, "unread", ["oncology"]),
    }
    params = ResultQueryParams(
        year=2024, has_abstract=True, saved=True, read_status="read", tags="key"
    )
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: states[pmid]
    )
    assert [item.pmid for item in filtered] == ["1"]


def test_apply_filters_empty_result_when_nothing_matches():
    items = [_item("1", year=2024), _item("2", year=2023)]
    params = ResultQueryParams(year=1990)
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: (False, DEFAULT_READ_STATUS, [])
    )
    assert filtered == []


def test_apply_filters_journal_is_substring_case_insensitive():
    items = [
        _item("1", journal="Nature Medicine"),
        _item("2", journal="Nature Reviews Cancer"),
        _item("3", journal="Cell"),
    ]
    params = ResultQueryParams(journal="nature medicine")
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: (False, DEFAULT_READ_STATUS, [])
    )
    # "Nature Medicine" 子串命中 "Nature Medicine"，但不应命中 "Nature Reviews Cancer"
    assert [item.pmid for item in filtered] == ["1"]


def test_apply_filters_publication_type_substring_match():
    items = [
        _item("1", publication_types=("Meta-Analysis",)),
        _item("2", publication_types=("Journal Article",)),
    ]
    params = ResultQueryParams(publication_type="meta-analysis")
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: (False, DEFAULT_READ_STATUS, [])
    )
    assert [item.pmid for item in filtered] == ["1"]


def test_apply_filters_author_substring_match():
    items = [
        _item("1", authors=("Kim J", "Lee S")),
        _item("2", authors=("Wang L",)),
    ]
    params = ResultQueryParams(author="kim")
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: (False, DEFAULT_READ_STATUS, [])
    )
    assert [item.pmid for item in filtered] == ["1"]


def test_apply_filters_has_abstract_false_matches_unknown_as_absent():
    # 旧快照 has_abstract 可能缺省为 False；未知即视为无摘要，能被筛选命中。
    items = [_item("1", has_abstract=True), _item("2", has_abstract=False)]
    params = ResultQueryParams(has_abstract=False)
    filtered = apply_filters(
        items, params, state_by_pmid=lambda pmid: (False, DEFAULT_READ_STATUS, [])
    )
    assert [item.pmid for item in filtered] == ["2"]


# 单元测试：排序逻辑
# ----------------------------------------------------------------------


def test_sort_newest_orders_by_year_desc_with_pmid_tiebreak():
    items = [
        _item("a", year=2020),
        _item("b", year=2023),
        _item("c", year=2023),
        _item("d", year=None),
    ]
    ranked = sort_items(
        items, ResultQueryParams(sort="newest"), current_year=2026
    )
    # 2023 两条按 pmid 次级键稳定排序；None 年份排最后。
    assert [entry.item.pmid for entry in ranked] == ["b", "c", "a", "d"]
    assert all(entry.sort_reason for entry in ranked)


def test_sort_classic_prefers_top_journal_and_recent_year():
    items = [
        _item("old", year=2010, journal="Nature"),
        _item("recent", year=2024, journal="Some Journal"),
        _item("none", year=None, journal="Science"),
    ]
    ranked = sort_items(
        items, ResultQueryParams(sort="classic"), current_year=2026
    )
    first = ranked[0].item
    # Nature 权威期刊 + 老年份 应排在"普通期刊 + 新年份"之前；None 排最后。
    assert first.pmid == "old"
    assert ranked[-1].item.pmid == "none"
    reasons = " ".join(entry.sort_reason for entry in ranked).lower()
    assert "top journal" in reasons
    assert "year unknown" in reasons


def test_sort_classic_is_stable_for_same_score():
    items = [
        _item("p1", year=2024, journal="Nature"),
        _item("p2", year=2024, journal="Nature"),
    ]
    ranked = sort_items(
        items, ResultQueryParams(sort="classic"), current_year=2026
    )
    # 同分（同期刊、同年份）时按 pmid 升序兜底，翻页不跳动。
    assert [entry.item.pmid for entry in ranked] == ["p1", "p2"]


def test_sort_custom_places_configured_first_others_keep_relevance():
    items = [
        _item("c", year=2024),
        _item("a", year=2024),
        _item("b", year=2024),
    ]
    order = {"b": 0, "c": 1}
    ranked = sort_items(
        items, ResultQueryParams(sort="custom"), current_year=2026, custom_order=order
    )
    # 已配置序号的条目按序号升序在前；未配置的 a 保持原顺序排在最后。
    assert [entry.item.pmid for entry in ranked] == ["b", "c", "a"]
    assert ranked[0].sort_reason.startswith("custom:")


def test_sort_relevance_preserves_input_order():
    items = [_item("2"), _item("1")]
    ranked = sort_items(
        items, ResultQueryParams(sort="relevance"), current_year=2026
    )
    assert [entry.item.pmid for entry in ranked] == ["2", "1"]
    assert ranked[0].sort_reason == (
        "relevance: ordered by PubMed default ranking for this search"
    )


# 接口测试：分页、筛选、用户态联动
# ----------------------------------------------------------------------


def _seed_result(client, items, total_count=3):
    """通过执行接口落库一批条目，返回 result_id。"""
    executor = client[1]
    executor.enqueue(items, total_count)
    created = client[0].post("/api/v1/literature-search", json=TASK_PAYLOAD)
    assert created.status_code == 201
    return created.json()["latest_result_id"]


def test_get_result_page_filters_and_paginates(api_client):
    client, executor = api_client
    items = [
        _item("1", year=2024, journal="Nature"),
        _item("2", year=2023, journal="Science"),
        _item("3", year=2022, journal="Cell"),
    ]
    result_id = _seed_result((client, executor), items)

    # 组合筛选 + 分页：筛选出 3 条中的 2 条，page_size=1 分页。
    page1 = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"year": 2024, "page": 1, "page_size": 1},
    )
    assert page1.status_code == 200
    payload = page1.json()
    assert payload["filtered_total"] == 1
    assert payload["total_count"] == 3
    assert len(payload["items"]) == 1
    assert payload["items"][0]["item"]["pmid"] == "1"
    assert payload["items"][0]["sort_reason"].startswith("relevance:")


def test_get_result_page_empty_result_and_out_of_range_page(api_client):
    client, executor = api_client
    items = [_item("1", year=2024), _item("2", year=2023)]
    result_id = _seed_result((client, executor), items)

    empty = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"year": 1990},
    )
    assert empty.status_code == 200
    assert empty.json()["filtered_total"] == 0
    assert empty.json()["items"] == []

    # 页码越界：items 为空而不是 500。
    beyond = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"page": 99},
    )
    assert beyond.status_code == 200
    assert beyond.json()["items"] == []
    assert beyond.json()["page"] == 99


def test_get_result_page_rejects_invalid_filter_params(api_client):
    client, executor = api_client
    items = [_item("1", year=2024)]
    result_id = _seed_result((client, executor), items)

    # 非法年份 → 422（Pydantic 白名单校验）。
    bad_year = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"year": 1800},
    )
    assert bad_year.status_code == 422

    # 非法排序 → 422。
    bad_sort = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"sort": "popularity"},
    )
    assert bad_sort.status_code == 422

    # 非法 page_size → 422。
    bad_page_size = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"page_size": 1000},
    )
    assert bad_page_size.status_code == 422


def test_item_state_write_read_and_filter_by_saved(api_client):
    client, executor = api_client
    items = [_item("1", year=2024), _item("2", year=2023)]
    result_id = _seed_result((client, executor), items)

    # 写入用户态：保存条目 1 并打标签。
    updated = client.patch(
        f"/api/v1/literature-search/{result_id}/items/1/state",
        json={"saved": True, "tags": ["oncology", "oncology"]},
    )
    assert updated.status_code == 200
    assert updated.json()["saved"] is True
    assert updated.json()["tags"] == ["oncology"]  # 去重

    # 按"是否已保存"筛选，只返回条目 1。
    filtered = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"saved": "true"},
    )
    assert filtered.status_code == 200
    pmids = [entry["item"]["pmid"] for entry in filtered.json()["items"]]
    assert pmids == ["1"]
    # 分页响应条目携带用户态。
    state = filtered.json()["items"][0]["state"]
    assert state["saved"] is True
    assert state["tags"] == ["oncology"]

    # 读取单条用户态。
    single = client.get(
        f"/api/v1/literature-search/{result_id}/items/1/state",
    )
    assert single.status_code == 200
    assert single.json()["read_status"] == DEFAULT_READ_STATUS


def test_item_state_update_keeps_unmodified_fields(api_client):
    client, executor = api_client
    items = [_item("1", year=2024)]
    result_id = _seed_result((client, executor), items)

    client.patch(
        f"/api/v1/literature-search/{result_id}/items/1/state",
        json={"saved": True, "tags": ["cancer"]},
    )
    # 只更新 read_status：saved 与 tags 保留。
    partial = client.patch(
        f"/api/v1/literature-search/{result_id}/items/1/state",
        json={"read_status": "read"},
    )
    assert partial.status_code == 200
    assert partial.json()["saved"] is True
    assert partial.json()["tags"] == ["cancer"]
    assert partial.json()["read_status"] == "read"


def test_item_state_write_to_missing_pmid_returns_404(api_client):
    client, executor = api_client
    items = [_item("1", year=2024)]
    result_id = _seed_result((client, executor), items)

    missing = client.patch(
        f"/api/v1/literature-search/{result_id}/items/99999/state",
        json={"saved": True},
    )
    assert missing.status_code == 404


def test_custom_sort_uses_persisted_custom_order(api_client):
    client, executor = api_client
    items = [_item("a", year=2024), _item("b", year=2024), _item("c", year=2024)]
    result_id = _seed_result((client, executor), items)

    # 设置自定义序号：b=0, c=1；a 未设置。
    client.patch(
        f"/api/v1/literature-search/{result_id}/items/b/state",
        json={"custom_order_index": 0},
    )
    client.patch(
        f"/api/v1/literature-search/{result_id}/items/c/state",
        json={"custom_order_index": 1},
    )

    custom = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"sort": "custom"},
    )
    assert custom.status_code == 200
    pmids = [entry["item"]["pmid"] for entry in custom.json()["items"]]
    assert pmids == ["b", "c", "a"]
    assert all(entry["sort_reason"].startswith("custom:") for entry in custom.json()["items"])


def test_newest_sort_reason_explains_year_unknown(api_client):
    client, executor = api_client
    items = [_item("known", year=2022), _item("unknown", year=None)]
    result_id = _seed_result((client, executor), items)

    newest = client.get(
        f"/api/v1/literature-search/{result_id}/results",
        params={"sort": "newest"},
    )
    assert newest.status_code == 200
    entries = newest.json()["items"]
    assert [entry["item"]["pmid"] for entry in entries] == ["known", "unknown"]
    assert "year unknown" in entries[-1]["sort_reason"]
