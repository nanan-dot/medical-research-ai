"""literature_search 阅读顺序规则分类测试（R2-WP08）。

覆盖验收项：综述优先、指南、原始研究、近年前沿、无文献类型兜底、人工顺序
持久化与重新生成不覆盖、规则理由可解释、证据特征只含真实字段。

设计说明：单元测试直接调用 reading_order 纯函数，验证分类与排序逻辑；
接口测试复用 test_filters 的脚本化执行器替身与临时 SQLite，避免真实网络，
并验证人工顺序经 PUT 保存后重新生成（不携带 manual_order）仍优先人工顺序。
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.literature_search.reading_order import (
    ClassifiedReadingItem,
    ReadingCategory,
    ReadingContext,
    apply_manual_order,
    classify_reading_item,
    rank_reading_order,
)
from app.modules.literature_search.schema import CitationItem

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


def _item(
    pmid: str,
    year: int = 2024,
    publication_types: tuple[str, ...] = ("Journal Article",),
    verified: bool = True,
) -> CitationItem:
    """构造一条带真实来源验证标记的替身条目（字段可覆盖以驱动分类）。"""
    return CitationItem(
        pmid=pmid,
        doi=None,
        title=f"Title {pmid}",
        authors=["Kim J"],
        journal="Nature Medicine",
        year=year,
        verified=verified,
        verified_by="pubmed",
        verified_on="2026-08-05T00:00:00+00:00",
        has_abstract=True,
        publication_types=list(publication_types),
    )


def _context(
    position: int, total: int = 3, fulltext_status: str | None = None
) -> ReadingContext:
    """构造规则分类上下文：current_year 固定 2026（与排序测试一致）。"""
    return ReadingContext(
        current_year=2026,
        position=position,
        total_items=total,
        fulltext_status=fulltext_status,
    )


# 单元测试：规则分类（证据金字塔优先级）
# ----------------------------------------------------------------------


def test_review_is_classified_first_with_explainable_features():
    item = _item("1", year=2021, publication_types=("Journal Article", "Review"))
    classified = classify_reading_item(item, _context(0))
    assert classified.category == "review"
    assert "publication_type=Review" in classified.evidence_features
    assert classified.evidence_features[0] == "verified=true"
    assert classified.reason.startswith("高质量综述")
    assert "建议最先阅读" in classified.reason
    assert "不确定性" in classified.reason


def test_guideline_takes_priority_over_review():
    # 罕见条目同时含 Guideline 与 Review：临床决策信号更具体，归指南。
    item = _item(
        "2",
        year=2020,
        publication_types=("Journal Article", "Review", "Practice Guideline"),
    )
    classified = classify_reading_item(item, _context(1))
    assert classified.category == "guideline"
    assert "publication_type=Practice Guideline" in classified.evidence_features
    assert classified.reason.startswith("指南或共识")


def test_original_research_meta_analysis_keyword():
    item = _item("3", year=2022, publication_types=("Journal Article", "Meta-Analysis"))
    assert classify_reading_item(item, _context(2)).category == "review"


def test_original_research_randomized_trial():
    item = _item(
        "4",
        year=2023,
        publication_types=("Journal Article", "Randomized Controlled Trial"),
    )
    classified = classify_reading_item(item, _context(0))
    assert classified.category == "original_research"
    assert (
        "publication_type=Randomized Controlled Trial" in classified.evidence_features
    )
    assert "建议在综述与指南之后阅读" in classified.reason


def test_original_research_observational_study():
    item = _item(
        "5", year=2023, publication_types=("Journal Article", "Observational Study")
    )
    assert classify_reading_item(item, _context(1)).category == "original_research"


def test_frontier_uses_recent_year_only():
    # 无明确类型但近年发表 → frontier；年份是时间信号而非质量信号。
    item = _item("6", year=2023, publication_types=("Journal Article",))
    classified = classify_reading_item(item, _context(2))
    assert classified.category == "frontier"
    assert "frontier=recent_5年" in classified.evidence_features
    assert "时间信号而非质量信号" in classified.reason


def test_old_journal_article_falls_back_to_highly_relevant():
    # 无明确类型且非近年 → 兜底 high_relevant（相关度信号）。
    item = _item("7", year=2010, publication_types=("Journal Article",))
    classified = classify_reading_item(item, _context(0))
    assert classified.category == "highly_relevant"
    assert "position=0" in classified.evidence_features
    assert classified.reason.startswith("与用户问题高度相关研究")


def test_frontier_needs_recent_year_not_just_presence():
    # year=None 的条目不进入前沿判定（无法证明近年），直接兜底。
    item = _item("8", year=None, publication_types=("Journal Article",))
    assert classify_reading_item(item, _context(0)).category == "highly_relevant"


def test_classification_never_uses_citation_metrics():
    # 证据特征只收录真实字段：verified / position / year / publication_type。
    item = _item("9", year=2024, publication_types=("Journal Article", "Review"))
    classified = classify_reading_item(
        item, _context(0, fulltext_status="local_pdf_available")
    )
    assert classified.category == "review"
    assert all(
        feature.startswith(
            ("verified=", "position=", "year=", "publication_type=", "frontier=")
        )
        for feature in classified.evidence_features
    )
    # 全文状态在理由里如实描述，不作为分类依据。
    assert "全文状态：local_pdf_available" in classified.reason


def test_unverified_item_records_no_verified_feature():
    item = _item("10", verified=False)
    classified = classify_reading_item(item, _context(0))
    assert all(
        not feature.startswith("verified=") for feature in classified.evidence_features
    )
    assert "未经验证" in classified.reason


# 单元测试：算法排序与人工顺序
# ----------------------------------------------------------------------


def _classified(
    pmid: str, category: ReadingCategory, position: int, year: int | None = 2024
) -> ClassifiedReadingItem:
    """构造一条已分类条目（供排序测试直接使用，避免重复分类噪音）。

    阅读顺序排序只看 category / position / year，evidence_features 与 reason
    不影响排序，测试里留空即可。
    """
    return ClassifiedReadingItem(
        pmid=pmid,
        category=category,
        evidence_features=(),
        reason="",
        position=position,
        year=year,
    )


def test_rank_reading_order_follows_evidence_pyramid():
    classified = [
        _classified("f", "frontier", 3),
        _classified("g", "guideline", 1),
        _classified("r", "review", 0),
        _classified("o", "original_research", 2),
        _classified("h", "highly_relevant", 4),
    ]
    ordered = rank_reading_order(classified)
    assert [entry.pmid for entry in ordered] == ["r", "g", "o", "f", "h"]


def test_rank_review_group_sorts_by_year_desc():
    classified = [
        _classified("old", "review", 0, year=2015),
        _classified("new", "review", 1, year=2024),
        _classified("unknown", "review", 2, year=None),
    ]
    ordered = rank_reading_order(classified)
    assert [entry.pmid for entry in ordered] == ["new", "old", "unknown"]


def test_rank_original_research_group_sorts_by_position():
    classified = [
        _classified("p2", "original_research", 2),
        _classified("p0", "original_research", 0),
        _classified("p1", "original_research", 1),
    ]
    ordered = rank_reading_order(classified)
    assert [entry.pmid for entry in ordered] == ["p0", "p1", "p2"]


def test_apply_manual_order_overrides_algorithm_order():
    classified = [
        _classified("r", "review", 0),
        _classified("g", "guideline", 1),
        _classified("o", "original_research", 2),
    ]
    ordered = apply_manual_order(classified, ["o", "r", "g"])
    assert [entry.pmid for entry in ordered] == ["o", "r", "g"]


def test_apply_manual_order_ignores_missing_pmids_and_appends_rest():
    classified = [
        _classified("r", "review", 0),
        _classified("o", "original_research", 1),
    ]
    # 消失的 PMID 被忽略；未在 manual_order 中的条目保留算法相对顺序追加末尾。
    ordered = apply_manual_order(classified, ["o", "missing"])
    assert [entry.pmid for entry in ordered] == ["o", "r"]


def test_apply_manual_order_empty_returns_algorithm_order():
    classified = [_classified("r", "review", 0), _classified("g", "guideline", 1)]
    assert apply_manual_order(classified, []) == list(classified)


# 接口测试：生成阅读顺序 + 人工顺序持久化
# ----------------------------------------------------------------------


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
        f"sqlite+aiosqlite:///{(tmp_path / 'reading_order.db').as_posix()}"
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


def _seed_result(client, executor, items):
    """通过执行接口落库一批条目，返回 result_id。"""
    executor.enqueue(items, len(items))
    created = client.post("/api/v1/literature-search", json=TASK_PAYLOAD)
    assert created.status_code == 201
    return created.json()["latest_result_id"]


def test_reading_order_rule_orders_by_evidence_pyramid(api_client):
    client, executor = api_client
    items = [
        _item(
            "orig",
            year=2023,
            publication_types=("Journal Article", "Randomized Controlled Trial"),
        ),
        _item("rev", year=2021, publication_types=("Journal Article", "Review")),
        _item(
            "guideline",
            year=2020,
            publication_types=("Journal Article", "Practice Guideline"),
        ),
    ]
    result_id = _seed_result(client, executor, items)

    generated = client.post(
        f"/api/v1/literature-search/{result_id}/reading-order", json={}
    )
    assert generated.status_code == 200
    payload = generated.json()
    assert payload["order_source"] == "rule"
    assert [entry["category"] for entry in payload["items"]] == [
        "review",
        "guideline",
        "original_research",
    ]
    # priority 1..n 连续编号；reason 与 evidence_features 可解释。
    for index, entry in enumerate(payload["items"]):
        assert entry["priority"] == index + 1
        assert entry["reason"]
        assert entry["evidence_features"]
        assert entry["pmid"]


def test_reading_order_manual_persisted_and_survives_regeneration(api_client):
    client, executor = api_client
    items = [
        _item(
            "orig",
            year=2023,
            publication_types=("Journal Article", "Randomized Controlled Trial"),
        ),
        _item("rev", year=2021, publication_types=("Journal Article", "Review")),
        _item(
            "guideline",
            year=2020,
            publication_types=("Journal Article", "Practice Guideline"),
        ),
    ]
    result_id = _seed_result(client, executor, items)

    # 保存人工顺序：把算法最后的原始研究拖到最前。
    saved = client.put(
        f"/api/v1/literature-search/{result_id}/reading-order/order",
        json={"manual_order": ["orig", "rev", "guideline"]},
    )
    assert saved.status_code == 200
    assert saved.json()["order_source"] == "manual"
    assert [entry["pmid"] for entry in saved.json()["items"]] == [
        "orig",
        "rev",
        "guideline",
    ]

    # 重新生成（不携带 manual_order）：仍优先人工顺序，不被算法覆盖。
    regenerated = client.post(
        f"/api/v1/literature-search/{result_id}/reading-order", json={}
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["order_source"] == "manual"
    assert [entry["pmid"] for entry in regenerated.json()["items"]] == [
        "orig",
        "rev",
        "guideline",
    ]


def test_reading_order_request_manual_overrides_each_time(api_client):
    client, executor = api_client
    items = [
        _item("a", year=2023, publication_types=("Journal Article", "Review")),
        _item(
            "b", year=2020, publication_types=("Journal Article", "Practice Guideline")
        ),
    ]
    result_id = _seed_result(client, executor, items)

    # 请求级 manual_order 优先，但只影响本次生成，不落库。
    generated = client.post(
        f"/api/v1/literature-search/{result_id}/reading-order",
        json={"manual_order": ["b", "a"]},
    )
    assert generated.status_code == 200
    assert [entry["pmid"] for entry in generated.json()["items"]] == ["b", "a"]

    # 不带 manual_order 的重新生成回到算法顺序（库中无人工顺序）。
    plain = client.post(f"/api/v1/literature-search/{result_id}/reading-order", json={})
    assert plain.status_code == 200
    assert [entry["pmid"] for entry in plain.json()["items"]] == ["a", "b"]


def test_reading_order_missing_result_returns_404(api_client):
    client, _executor = api_client
    missing = client.post("/api/v1/literature-search/99999/reading-order", json={})
    assert missing.status_code == 404


def test_reading_order_keeps_manual_orders_isolated_by_duplicate_mode(api_client):
    client, executor = api_client
    result_id = _seed_result(client, executor, [_item("same"), _item("same"), _item("other")])
    client.put(f"/api/v1/literature-search/results/{result_id}/deduplication")
    all_saved = client.put(
        f"/api/v1/literature-search/{result_id}/reading-order/order",
        json={"manual_order": ["other", "same"], "duplicate_mode": "all"},
    )
    consolidated = client.post(
        f"/api/v1/literature-search/{result_id}/reading-order",
        json={"duplicate_mode": "consolidated"},
    )
    assert all_saved.status_code == 200
    assert consolidated.status_code == 200
    assert all_saved.json()["duplicate_mode"] == "all"
    assert consolidated.json()["duplicate_mode"] == "consolidated"
    assert consolidated.json()["order_source"] == "rule"
    # consolidated 视图不含被折叠的重复成员，只有规范记录与独立条目。
    assert [entry["pmid"] for entry in consolidated.json()["items"]] == ["same", "other"]
