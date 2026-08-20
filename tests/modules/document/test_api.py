import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource


@pytest.fixture
def api_context(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    root = tmp_path / "source"
    root.mkdir()
    paper = root / "paper.md"
    paper.write_text("API test fixture", encoding="utf-8")

    async def prepare() -> int:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            source = KnowledgeSource(
                name="source",
                source_type="local_folder",
                root_path=str(root),
                normalized_root_path=str(root).casefold(),
                enabled=True,
                sync_status="idle",
            )
            session.add(source)
            await session.flush()
            stat = paper.stat()
            document = Document(
                knowledge_source_id=source.id,
                file_path=paper.name,
                normalized_file_path=paper.name,
                file_hash="a" * 64,
                file_size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime, UTC),
                modified_time_ns=stat.st_mtime_ns,
                scan_state="outdated",
                parse_status="failed",
                index_status="outdated",
                error_code="parse_failed",
                error_message="Safe failure",
            )
            session.add(document)
            await session.commit()
            return document.id

    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    document_id = asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, document_id, paper
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_document_list_detail_retry_and_delete_index_api(api_context, monkeypatch):
    client, document_id, paper = api_context
    listed = client.get(
        "/api/v1/documents", params={"parse_status": "failed", "limit": 10}
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["error_code"] == "parse_failed"

    detail = client.get(f"/api/v1/documents/{document_id}")
    assert detail.status_code == 200
    retried = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert retried.status_code == 200
    assert retried.json()["parse_status"] == "succeeded"
    duplicate = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert duplicate.status_code == 409

    indexed_ids: list[int] = []

    async def fake_index(_, requested_document_id: int) -> None:
        indexed_ids.append(requested_document_id)

    monkeypatch.setattr(
        "app.modules.document.router.DocumentIndexService.index", fake_index
    )
    retried_index = client.post(f"/api/v1/documents/{document_id}/retry-index")
    assert retried_index.status_code == 200
    assert indexed_ids == [document_id]

    deleted_index = client.delete(f"/api/v1/documents/{document_id}/index")
    assert deleted_index.status_code == 200
    assert deleted_index.json()["index_status"] == "pending"
    assert paper.read_text(encoding="utf-8") == "API test fixture"


def test_document_list_filters_by_knowledge_source(api_context):
    client, document_id, _ = api_context
    detail = client.get(f"/api/v1/documents/{document_id}")
    source_id = detail.json()["knowledge_source_id"]

    filtered = client.get("/api/v1/documents", params={"knowledge_source_id": source_id})
    unfiltered = client.get("/api/v1/documents")
    missing_source = client.get("/api/v1/documents", params={"knowledge_source_id": 99999})

    assert [item["id"] for item in filtered.json()["items"]] == [document_id]
    assert [item["id"] for item in unfiltered.json()["items"]] == [document_id]
    assert missing_source.json()["items"] == []
    assert missing_source.json()["total"] == 0


def test_repair_submission_is_idempotent(api_context) -> None:
    """AC-12: repeated repair submits one active durable document task."""
    client, document_id, _ = api_context

    first = client.post(f"/api/v1/documents/{document_id}/repair")
    second = client.post(f"/api/v1/documents/{document_id}/repair")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["task_id"] == second.json()["task_id"]
    tasks = client.get("/api/v1/tasks", params={"status": "queued"})
    assert tasks.status_code == 200
    assert tasks.json()["total"] == 1


def test_parse_and_content_summary_api(api_context):
    client, document_id, paper = api_context
    paper.write_text("# API Notes\nBody", encoding="utf-8")
    retried = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert retried.status_code == 200
    summary = client.get(f"/api/v1/documents/{document_id}/content-summary")
    assert summary.status_code == 200
    assert summary.json()["section_headings"] == ["API Notes"]


def test_current_paper_workflow_query_validation_and_missing_results(api_context):
    client, document_id, _ = api_context
    assert client.get("/api/v1/documents", params={"query": "x" * 201}).status_code == 422
    assert client.get("/api/v1/paper-analysis/latest", params={"document_id": 0}).status_code == 422
    assert client.get("/api/v1/conversations/latest", params={"document_id": 0}).status_code == 422

    analysis = client.get("/api/v1/paper-analysis/latest", params={"document_id": document_id})
    conversation = client.get("/api/v1/conversations/latest", params={"document_id": document_id})
    assert analysis.status_code == 404 and analysis.json()["error"]["code"] == "not_found"
    assert conversation.status_code == 404 and conversation.json()["error"]["code"] == "not_found"
