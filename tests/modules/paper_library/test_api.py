"""论文库冻结规格的后端验收测试。"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.integrations.paperqa2.exceptions import PaperQA2OperationError
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.model import PaperActivity, PaperLibraryMember
from app.modules.research_context.model import ResearchContext


@pytest.fixture
async def paper_library_client(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'papers.db').as_posix()}"
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

    async with factory() as session:
        source = KnowledgeSource(
            name="Test source",
            source_type="local",
            root_path="D:/test-source",
            normalized_root_path="d:/test-source",
        )
        session.add(source)
        await session.flush()
        document = Document(
            knowledge_source_id=source.id,
            file_path="D:/test-source/paper.pdf",
            normalized_file_path="d:/test-source/paper.pdf",
            file_hash="a" * 64,
            file_size=100,
            modified_time=datetime.now(UTC),
            modified_time_ns=1,
            parse_status="succeeded",
            index_status="succeeded",
            paperqa_index_key="idx-paper-library-test",
        )
        session.add(document)
        await session.flush()
        resource_only_document = Document(
            knowledge_source_id=source.id,
            file_path="D:/test-source/resource-only-paper.pdf",
            normalized_file_path="d:/test-source/resource-only-paper.pdf",
            file_hash="b" * 64,
            file_size=200,
            modified_time=datetime.now(UTC),
            modified_time_ns=2,
            parse_status="succeeded",
            index_status="succeeded",
            paperqa_index_key="idx-resource-only-paper",
        )
        session.add(resource_only_document)
        await session.flush()
        paper_with_pdf = LibraryItem(
            pmid="1001", doi="10.1000/test-one", title="Kidney trial",
            authors="Researcher A; Researcher B", journal="Test Journal", year=2025,
            paper_type="RCT", journal_quartile="Q1", source_search_id=None,
            document_id=document.id, fulltext_status="metadata_only",
            fulltext_status_reason="No verified full text",
        )
        metadata_only_paper = LibraryItem(
            pmid="1002", doi=None, title="Review paper", authors="Researcher C",
            journal="Review Journal", year=2024, paper_type="Systematic Review",
            source_search_id=None, fulltext_status="unavailable",
            fulltext_status_reason="Full text unavailable",
        )
        historical_search_save = LibraryItem(
            pmid="1003", doi=None, title="Historical saved search result",
            source_search_id=99, fulltext_status="metadata_only",
            fulltext_status_reason="Saved before paper library membership existed",
        )
        session.add_all([
            paper_with_pdf, metadata_only_paper, historical_search_save,
            ResearchContext(name="CKD research", description="Test context"),
            ResearchContext(name="Diabetes research", description="Second context"),
            # 历史 pending 后续已成功，论文库只能把最新一次作为当前分析状态。
            PaperAnalysis(document_id=document.id, analysis_status="pending", template_version="v1", model_version="test", generation=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)),
            PaperAnalysis(document_id=document.id, analysis_status="succeeded", template_version="v1", model_version="test", generation=2, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)),
        ])
        await session.flush()
        session.add_all([
            PaperLibraryMember(library_item_id=paper_with_pdf.id, import_source="resource_library"),
            PaperLibraryMember(library_item_id=metadata_only_paper.id, import_source="external_identifier"),
            PaperActivity(library_item_id=paper_with_pdf.id, kind="analysis_completed"),
        ])
        await session.commit()

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_items_summary_and_unclassified_are_derived(paper_library_client):
    client = paper_library_client
    summary = client.get("/api/v1/paper-library/summary")
    items = client.get("/api/v1/paper-library/items", params={"view": "unclassified"})

    assert summary.status_code == 200
    assert summary.json()["all"] == 2
    assert summary.json()["unclassified"] == 2
    assert items.status_code == 200
    assert items.json()["total"] == 2
    assert items.json()["items"][0]["analysis_progress"] is None


def test_saved_search_result_is_hidden_until_user_explicitly_adds_it(
    paper_library_client,
):
    client = paper_library_client

    before = client.get("/api/v1/paper-library/items")
    added = client.post("/api/v1/paper-library/items", json={"pmid": "1003"})
    after = client.get("/api/v1/paper-library/items")

    assert before.status_code == 200
    assert {item["pmid"] for item in before.json()["items"]} == {"1001", "1002"}
    assert added.status_code == 201
    assert added.json()["outcome"] == "created"
    assert {item["pmid"] for item in after.json()["items"]} == {
        "1001",
        "1002",
        "1003",
    }


def test_resource_library_document_is_visible_only_after_explicit_add(
    paper_library_client,
):
    client = paper_library_client

    before = client.get("/api/v1/paper-library/items")
    created = client.post("/api/v1/paper-library/items", json={"document_id": 2})
    duplicate = client.post("/api/v1/paper-library/items", json={"document_id": 2})

    assert before.status_code == 200
    assert all(item["document_id"] != 2 for item in before.json()["items"])
    assert created.status_code == 201
    assert created.json()["outcome"] == "created"
    assert created.json()["item"]["document_id"] == 2
    assert duplicate.status_code == 201
    assert duplicate.json()["outcome"] == "already_exists"


def test_reading_state_validates_and_records_activity(paper_library_client):
    client = paper_library_client
    invalid = client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={"status": "read", "progress_percent": 60, "current_section": "Results"},
    )
    assert invalid.status_code == 422

    updated = client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={
            "status": "reading",
            "progress_percent": 60,
            "current_section": "Results",
        },
    )
    activities = client.get("/api/v1/paper-library/items/1/activities")
    assert updated.status_code == 200
    assert updated.json()["reading_progress_percent"] == 60
    assert activities.status_code == 200
    assert activities.json()[0]["kind"] == "reading_progressed"


def test_research_relation_uses_optimistic_lock(paper_library_client):
    client = paper_library_client
    created = client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={
            "role": "core_evidence",
            "note": "Primary evidence",
            "expected_version": None,
        },
    )
    assert created.status_code == 200
    assert created.json()["version"] == 1

    conflict = client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={"role": "background_support", "note": None, "expected_version": 0},
    )
    assert conflict.status_code == 409


def test_compound_filter_uses_or_within_group_and_and_between_groups(
    paper_library_client,
):
    client = paper_library_client
    client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={
            "status": "reading",
            "progress_percent": 20,
            "current_section": "Methods",
        },
    )
    response = client.get(
        "/api/v1/paper-library/items",
        params=[
            ("reading_status", "reading"),
            ("reading_status", "read"),
            ("paper_type", "RCT"),
        ],
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["pmid"] == "1001"


def test_unread_includes_missing_state_and_unclassified_includes_missing_role(
    paper_library_client,
):
    client = paper_library_client
    relation = client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={"role": None, "note": None, "expected_version": None},
    )
    unread = client.get(
        "/api/v1/paper-library/items", params={"reading_status": "unread"}
    )
    pending = client.get("/api/v1/paper-library/items", params={"view": "unclassified"})
    assert relation.status_code == 200
    assert unread.json()["total"] == 2
    assert pending.json()["total"] == 2


def test_add_by_doi_is_idempotent_and_overview_lists_all_relations(
    paper_library_client,
):
    client = paper_library_client
    created = client.post(
        "/api/v1/paper-library/items", json={"doi": "https://doi.org/10.5555/Example"}
    )
    duplicate = client.post(
        "/api/v1/paper-library/items", json={"doi": "10.5555/example"}
    )
    assert created.status_code == 201
    assert created.json()["outcome"] == "created"
    assert duplicate.status_code == 201
    assert duplicate.json()["outcome"] == "already_exists"
    assert duplicate.json()["item"]["id"] == created.json()["item"]["id"]


def test_relation_delete_respects_version(paper_library_client):
    client = paper_library_client
    created = client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={"role": "core_evidence", "note": None, "expected_version": None},
    )
    wrong = client.delete(
        "/api/v1/paper-library/items/1/research-relations/1",
        params={"expected_version": 2},
    )
    removed = client.delete(
        "/api/v1/paper-library/items/1/research-relations/1",
        params={"expected_version": created.json()["version"]},
    )
    assert wrong.status_code == 409
    assert removed.status_code == 204


def test_tags_are_persisted_filterable_and_exposed_as_facets(paper_library_client):
    client = paper_library_client
    updated = client.put(
        "/api/v1/paper-library/items/1/tags",
        json={"tags": ["肾病", " 核心 ", "肾病"]},
    )
    filtered = client.get("/api/v1/paper-library/items", params={"tag": "肾病"})
    facets = client.get("/api/v1/paper-library/facets")

    assert updated.status_code == 200
    assert updated.json() == ["肾病", "核心"]
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["tags"] == ["核心", "肾病"]
    assert facets.status_code == 200
    assert {row["value"]: row["count"] for row in facets.json()["tags"]}["肾病"] == 1


def test_research_role_and_context_filters_apply_to_same_relation(paper_library_client):
    client = paper_library_client
    client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={"role": "core_evidence", "note": None, "expected_version": None},
    )
    matched = client.get(
        "/api/v1/paper-library/items",
        params={"research_role": "core_evidence", "research_id": 1},
    )
    missed = client.get(
        "/api/v1/paper-library/items",
        params={"research_role": "background_support", "research_id": 1},
    )
    assert matched.json()["total"] == 1
    assert missed.json()["total"] == 0


def test_capability_projection_is_truthful_with_ready_document(paper_library_client):
    item = paper_library_client.get("/api/v1/paper-library/items").json()["items"][0]
    assert item["can_read"] is True
    assert item["can_analyze"] is True
    assert item["capability_reason"] is None


def test_current_analysis_view_ignores_obsolete_active_attempts(paper_library_client):
    response = paper_library_client.get(
        "/api/v1/paper-library/items", params={"view": "analyzing"}
    )
    item = paper_library_client.get("/api/v1/paper-library/items").json()["items"][0]

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert item["analysis_status"] == "completed"


def test_recent_view_uses_real_analysis_activity(paper_library_client):
    response = paper_library_client.get(
        "/api/v1/paper-library/items", params={"view": "recent"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == 1


def test_added_at_sort_and_invalid_enum_parameters(paper_library_client):
    client = paper_library_client
    created = client.post("/api/v1/paper-library/items", json={"doi": "10.5555/new"})
    sorted_items = client.get(
        "/api/v1/paper-library/items", params={"sort": "added_at"}
    )
    invalid = client.get(
        "/api/v1/paper-library/items", params={"analysis_status": "unknown"}
    )

    assert created.status_code == 201
    assert sorted_items.status_code == 200
    assert sorted_items.json()["items"][0]["id"] == created.json()["item"]["id"]
    assert invalid.status_code == 422


def test_search_includes_paper_tags(paper_library_client):
    client = paper_library_client
    client.put("/api/v1/paper-library/items/1/tags", json={"tags": ["肾病核心"]})
    response = client.get("/api/v1/paper-library/items", params={"query": "肾病"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_multiple_tags_use_or_then_cross_group_uses_and(paper_library_client):
    client = paper_library_client
    client.put("/api/v1/paper-library/items/1/tags", json={"tags": ["A"]})
    client.put("/api/v1/paper-library/items/2/tags", json={"tags": ["B"]})
    client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={"status": "reading", "progress_percent": 20, "current_section": "Methods"},
    )

    tags_only = client.get(
        "/api/v1/paper-library/items", params=[("tag", "A"), ("tag", "B")]
    )
    tags_and_reading = client.get(
        "/api/v1/paper-library/items",
        params=[("tag", "A"), ("tag", "B"), ("reading_status", "reading")],
    )
    facets = client.get(
        "/api/v1/paper-library/facets", params=[("tag", "A"), ("tag", "B")]
    )

    assert {item["id"] for item in tags_only.json()["items"]} == {1, 2}
    assert [item["id"] for item in tags_and_reading.json()["items"]] == [1]
    assert {row["value"]: row["count"] for row in facets.json()["tags"]} == {
        "A": 1,
        "B": 1,
    }


def test_filtered_relation_is_projected_as_primary_relation(paper_library_client):
    client = paper_library_client
    client.put(
        "/api/v1/paper-library/items/1/research-relations/1",
        json={"role": "background_support", "note": None, "expected_version": None},
    )
    client.put(
        "/api/v1/paper-library/items/1/research-relations/2",
        json={"role": "core_evidence", "note": None, "expected_version": None},
    )
    response = client.get(
        "/api/v1/paper-library/items",
        params={"research_id": 2, "research_role": "core_evidence"},
    )

    item = response.json()["items"][0]
    assert item["primary_relation"]["research_context_id"] == 2
    assert item["primary_relation"]["role"] == "core_evidence"
    assert item["additional_relation_count"] == 1


def test_duplicate_reading_progress_does_not_duplicate_activity(paper_library_client):
    payload = {"status": "reading", "progress_percent": 45, "current_section": "Results"}
    first = paper_library_client.patch(
        "/api/v1/paper-library/items/1/reading-state", json=payload
    )
    second = paper_library_client.patch(
        "/api/v1/paper-library/items/1/reading-state", json=payload
    )
    activities = paper_library_client.get(
        "/api/v1/paper-library/items/1/activities"
    ).json()

    assert first.status_code == second.status_code == 200
    assert [row["kind"] for row in activities].count("reading_progressed") == 1
    item = paper_library_client.get("/api/v1/paper-library/items").json()["items"][0]
    assert item["preferred_work_action"] == "reading"
    assert item["last_work_at"] is not None
    assert item["reading_entry"]["action"] == "continue"


def test_unavailable_item_exposes_separate_entry_reasons(paper_library_client):
    items = paper_library_client.get("/api/v1/paper-library/items").json()["items"]
    unavailable = next(item for item in items if item["id"] == 2)

    assert unavailable["preferred_work_action"] == "reading"
    assert unavailable["reading_entry"]["enabled"] is False
    assert unavailable["analysis_entry"]["enabled"] is False
    assert unavailable["reading_entry"]["reason"]


def test_unread_reset_clears_section_without_becoming_recent_work(paper_library_client):
    client = paper_library_client
    client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={"status": "reading", "progress_percent": 30, "current_section": "Results"},
    )
    reset = client.patch(
        "/api/v1/paper-library/items/1/reading-state",
        json={"status": "unread", "progress_percent": 0, "current_section": "Results"},
    )

    assert reset.status_code == 200
    assert reset.json()["current_section"] is None
    assert reset.json()["last_read_at"] is None


def test_failed_analysis_is_committed_with_library_activity(
    paper_library_client, monkeypatch
):
    class FailingClient:
        async def ask(self, index, question):
            raise PaperQA2OperationError("simulated upstream failure")

    monkeypatch.setattr(
        "app.modules.paper_analysis.service.create_paperqa2_client",
        lambda: FailingClient(),
    )
    failed = paper_library_client.post(
        "/api/v1/paper-analysis", json={"document_id": 1}
    )
    latest = paper_library_client.get(
        "/api/v1/paper-analysis/latest", params={"document_id": 1}
    )
    activities = paper_library_client.get(
        "/api/v1/paper-library/items/1/activities"
    ).json()

    assert failed.status_code == 409
    assert latest.status_code == 200
    assert latest.json()["analysis_status"] == "failed"
    assert activities[0]["kind"] == "analysis_failed"
