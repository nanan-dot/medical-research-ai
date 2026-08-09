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


def test_document_list_detail_retry_and_delete_index_api(api_context):
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
    assert retried.json()["parse_status"] == "pending"
    duplicate = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert duplicate.status_code == 409

    deleted_index = client.delete(f"/api/v1/documents/{document_id}/index")
    assert deleted_index.status_code == 200
    assert deleted_index.json()["index_status"] == "pending"
    assert paper.read_text(encoding="utf-8") == "API test fixture"


def test_parse_and_content_summary_api(api_context):
    client, document_id, paper = api_context
    paper.write_text("# API Notes\nBody", encoding="utf-8")
    retried = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert retried.status_code == 200
    parsed = client.post(f"/api/v1/documents/{document_id}/parse")
    assert parsed.status_code == 200
    assert parsed.json()["section_headings"] == ["API Notes"]
    summary = client.get(f"/api/v1/documents/{document_id}/content-summary")
    assert summary.status_code == 200
    assert summary.json() == parsed.json()
