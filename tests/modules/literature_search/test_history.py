"""literature_search 检索任务与历史 API 测试。

覆盖 R2-WP04 验收：创建任务、失败任务、重跑版本、历史分页、检索式保存、
结果变化摘要、检索策略导出。通过替换 service 的 pubmed_executor 为脚本化
替身避免真实网络，同时用临时 SQLite 覆盖 get_session 依赖，确保不写入开发库。
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.integrations.pubmed.exceptions import PubMedError
from app.main import app
from app.modules.literature_search.schema import CitationItem
from app.modules.literature_search.service import strategy_fingerprint_from_snapshot

TASK_PAYLOAD = {
    "original_query": "胃癌 EGFR 免疫治疗",
    "structured_query": json.dumps(
        {"topic": "胃癌 EGFR 免疫治疗", "disease": "胃癌"}, ensure_ascii=False
    ),
    "search_string": (
        '"stomach neoplasms"[Title/Abstract] AND "EGFR"[Title/Abstract] AND immunotherapy'
    ),
    "database": "pubmed",
    "filters": json.dumps({"language": "English"}, ensure_ascii=False),
    "model_version": "search-intent-v1",
    "user_edits": json.dumps(
        {"disease": ["胃癌", "gastric cancer"]}, ensure_ascii=False
    ),
    "retmax": 20,
}


def _item(pmid: str, year: int = 2024) -> CitationItem:
    """构造一条带 verified 标记的替身条目（PMID 各不相同以驱动变化摘要）。"""
    return CitationItem(
        pmid=pmid,
        doi=None,
        title=f"Title {pmid}",
        authors=["Kim J"],
        journal="Nature Medicine",
        year=year,
        verified=True,
        verified_by="pubmed",
        verified_on="2026-08-05T00:00:00+00:00",
    )


class _ScriptedExecutor:
    """脚本化替身执行器：按调用顺序返回预置结果或抛出预置异常。

    设计说明：跨请求共享同一实例（service 每次请求重建，但 __init__ 被
    替换为注入本实例），因此 create → rerun 的多次调用按 index 依次消费。
    """

    def __init__(self) -> None:
        self.steps: list[tuple[list[CitationItem], int] | Exception] = []
        self.index = 0

    def enqueue(self, items: list[CitationItem], total_count: int) -> None:
        self.steps.append((items, total_count))

    def enqueue_error(self, exc: Exception) -> None:
        self.steps.append(exc)

    async def execute(self, query: str, *, retmax: int = 20):
        if self.index >= len(self.steps):
            raise AssertionError("executor called more times than scripted steps")
        step = self.steps[self.index]
        self.index += 1
        if isinstance(step, Exception):
            raise step
        return step


@pytest.fixture
async def api_client(tmp_path, monkeypatch):
    from app.modules.literature_search.service import LiteratureSearchService

    executor = _ScriptedExecutor()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'history.db').as_posix()}"
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


def test_create_task_persists_input_snapshot_and_search_string(api_client):
    client, executor = api_client
    executor.enqueue([_item("39000401")], 1)

    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "succeeded"
    assert payload["result_count"] == 1
    assert payload["latest_result_id"] is not None
    assert payload["searched_at"] is not None
    # 检索式与完整输入快照被保存，重跑可直接复用
    assert payload["search_string"] == TASK_PAYLOAD["search_string"]
    assert payload["structured_query"] == TASK_PAYLOAD["structured_query"]
    assert payload["model_version"] == TASK_PAYLOAD["model_version"]
    assert payload["user_edits"] == TASK_PAYLOAD["user_edits"]
    assert payload["filters"] == TASK_PAYLOAD["filters"]
    assert len(payload["versions"]) == 1
    assert payload["versions"][0]["version"] == 1
    assert payload["versions"][0]["result_count"] == 1
    assert payload["versions"][0]["change"] is None
    assert payload["operation"] == "created"


def test_create_task_reuses_exact_strategy_as_next_version(api_client):
    client, executor = api_client
    executor.enqueue([_item("10001")], 1)
    executor.enqueue([_item("10002")], 1)

    first = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    repeated = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)

    assert repeated.status_code == 201
    payload = repeated.json()
    assert payload["operation"] == "reused"
    assert payload["id"] == first["id"]
    assert payload["new_result_id"] == payload["latest_result_id"]
    assert payload["versions"][-1]["version"] == 2
    assert payload["change"]["added_pmids"] == ["10002"]
    assert client.get("/api/v1/literature-search").json()["total"] == 1
    detail = client.get(f"/api/v1/literature-search/{first['id']}").json()
    assert [version["version"] for version in detail["versions"]] == [1, 2]
    assert detail["versions"][0]["result_id"] == first["latest_result_id"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filters", '{"language":"Chinese"}'),
        ("retmax", 10),
        ("user_edits", '{"disease":["new term"]}'),
        ("model_version", "search-intent-v2"),
        ("search_string", "new exact query"),
    ],
)
def test_create_task_does_not_merge_changed_strategy(api_client, field, value):
    client, executor = api_client
    executor.enqueue([_item("10001")], 1)
    executor.enqueue([_item("10002")], 1)
    changed = {**TASK_PAYLOAD, field: value}

    first = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    second = client.post("/api/v1/literature-search", json=changed).json()

    assert first["id"] != second["id"]
    assert second["operation"] == "created"
    assert client.get("/api/v1/literature-search").json()["total"] == 2


def test_create_task_normalizes_json_snapshot_order(api_client):
    client, executor = api_client
    executor.enqueue([_item("10001")], 1)
    executor.enqueue([_item("10002")], 1)
    first_payload = {**TASK_PAYLOAD, "filters": '{ "year": 2024, "language": "English" }'}
    same_payload = {**TASK_PAYLOAD, "filters": '{"language":"English","year":2024}'}

    first = client.post("/api/v1/literature-search", json=first_payload).json()
    second = client.post("/api/v1/literature-search", json=same_payload).json()

    assert second["operation"] == "reused"
    assert second["id"] == first["id"]


def test_strategy_fingerprint_normalizes_user_edit_whitespace_and_order():
    first = strategy_fingerprint_from_snapshot(
        database="pubmed", search_string="query", filters="{}", retmax=20,
        user_edits='{"disease": [" 胃癌 ", "", "gastric cancer"], "target": ["EGFR"]}',
        model_version="v1", structured_query="{}", original_query="topic",
    )
    second = strategy_fingerprint_from_snapshot(
        database="pubmed", search_string="query", filters="{}", retmax=20,
        user_edits=' { "target" : [ "EGFR" ], "disease" : [ "gastric cancer", "胃癌" ] } ',
        model_version="v1", structured_query="{}", original_query="topic",
    )

    assert first == second


def test_strategy_fingerprint_keeps_semantically_different_user_edits_distinct():
    shared = {
        "database": "pubmed", "search_string": "query", "filters": "{}", "retmax": 20,
        "model_version": "v1", "structured_query": "{}", "original_query": "topic",
    }

    assert strategy_fingerprint_from_snapshot(
        **shared, user_edits='{"disease":["gastric cancer"]}'
    ) != strategy_fingerprint_from_snapshot(
        **shared, user_edits='{"disease":["stomach neoplasms"]}'
    )


def test_strategy_fingerprint_tolerates_invalid_user_edits_json():
    fingerprint = strategy_fingerprint_from_snapshot(
        database="pubmed", search_string="query", filters="{}", retmax=20,
        user_edits="{invalid json", model_version="v1", structured_query="{}", original_query="topic",
    )

    assert len(fingerprint) == 64


def test_result_page_exposes_saved_library_fulltext_status(api_client):
    client, executor = api_client
    executor.enqueue([_item("39000401")], 1)

    task = client.post("/api/v1/literature-search", json=TASK_PAYLOAD).json()
    result_id = task["latest_result_id"]
    saved = client.post(
        f"/api/v1/literature-results/{result_id}/save", json={"pmid": "39000401"}
    )
    assert saved.status_code == 200

    response = client.get(f"/api/v1/literature-search/{result_id}/results")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["item"]["abstract"] is None
    assert item["library_item"]["fulltext_status"] == "metadata_only"


def test_failed_task_records_error_and_has_no_version(api_client):
    client, executor = api_client
    executor.enqueue_error(PubMedError("ESearch failed"))

    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "failed"
    assert "ESearch failed" in payload["error_message"]
    assert payload["versions"] == []
    assert payload["latest_result_id"] is None
    assert payload["searched_at"] is None


def test_rerun_creates_new_version_without_overwriting(api_client):
    client, executor = api_client
    executor.enqueue([_item("10001")], 1)
    executor.enqueue([_item("10002")], 1)

    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    task_id = created.json()["id"]
    first_result_id = created.json()["latest_result_id"]

    rerun = client.post(f"/api/v1/literature-search/{task_id}/rerun")
    assert rerun.status_code == 200
    payload = rerun.json()
    assert payload["task"]["status"] == "succeeded"
    # 重跑创建新结果引用，不覆盖旧版本
    assert payload["task"]["latest_result_id"] != first_result_id
    assert payload["new_result_id"] == payload["task"]["latest_result_id"]
    assert payload["change"]["added_pmids"] == ["10002"]
    assert payload["change"]["removed_pmids"] == ["10001"]
    assert payload["change"]["added_count"] == 1
    assert payload["change"]["removed_count"] == 1

    detail = client.get(f"/api/v1/literature-search/{task_id}").json()
    assert [version["version"] for version in detail["versions"]] == [1, 2]
    assert detail["versions"][1]["change"]["added_pmids"] == ["10002"]
    assert detail["versions"][1]["change"]["removed_pmids"] == ["10001"]


def test_rerun_reports_result_count_delta(api_client):
    client, executor = api_client
    executor.enqueue([_item("10001"), _item("10002")], 5)
    executor.enqueue([_item("10002")], 3)

    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    task_id = created.json()["id"]

    rerun = client.post(f"/api/v1/literature-search/{task_id}/rerun").json()
    assert rerun["change"]["previous_count"] == 5
    assert rerun["change"]["current_count"] == 3
    assert rerun["change"]["count_delta"] == -2
    assert rerun["change"]["added_pmids"] == []
    assert rerun["change"]["removed_pmids"] == ["10001"]


def test_rerun_failed_task_succeeds_without_change_baseline(api_client):
    client, executor = api_client
    executor.enqueue_error(PubMedError("first attempt failed"))
    executor.enqueue([_item("10001")], 1)

    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    task_id = created.json()["id"]
    assert created.json()["status"] == "failed"

    rerun = client.post(f"/api/v1/literature-search/{task_id}/rerun")
    assert rerun.status_code == 200
    payload = rerun.json()
    assert payload["task"]["status"] == "succeeded"
    # 失败任务重跑没有旧版本基线，change 为 None
    assert payload["change"] is None
    assert payload["new_result_id"] > 0


def test_list_tasks_paginates_and_orders_by_recency(api_client):
    client, executor = api_client
    for i in range(3):
        executor.enqueue([_item(f"{i:05d}")], 1)
        client.post(
            "/api/v1/literature-search",
            json={**TASK_PAYLOAD, "original_query": f"{TASK_PAYLOAD['original_query']} {i}"},
        )

    page1 = client.get("/api/v1/literature-search", params={"offset": 0, "limit": 2})
    assert page1.status_code == 200
    payload1 = page1.json()
    assert payload1["total"] == 3
    assert len(payload1["items"]) == 2
    # 最新创建的任务排在最前（id 倒序兜底同一时间戳）
    ids_desc = [item["id"] for item in payload1["items"]]
    assert ids_desc == sorted(ids_desc, reverse=True)

    page2 = client.get("/api/v1/literature-search", params={"offset": 2, "limit": 2})
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 1


def test_export_strategy_requires_successful_search(api_client):
    client, executor = api_client
    executor.enqueue([_item("10001")], 1)
    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    task_id = created.json()["id"]

    strategy = client.get(f"/api/v1/literature-search/{task_id}/strategy")
    assert strategy.status_code == 200
    payload = strategy.json()
    assert payload["original_query"] == TASK_PAYLOAD["original_query"]
    assert payload["search_string"] == TASK_PAYLOAD["search_string"]
    assert payload["database"] == "pubmed"
    assert payload["result_count"] == 1
    assert payload["searched_at"] is not None

    # 从未成功的任务无可导出检索日期 → 404，不伪造时间与结果数
    executor.enqueue_error(PubMedError("boom"))
    failed = client.post(
        "/api/v1/literature-search",
        json={**TASK_PAYLOAD, "model_version": "search-intent-v2"},
    )
    failed_id = failed.json()["id"]
    assert failed.json()["status"] == "failed"
    missing = client.get(f"/api/v1/literature-search/{failed_id}/strategy")
    assert missing.status_code == 404
