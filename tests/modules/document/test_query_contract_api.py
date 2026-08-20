"""Acceptance tests for the document-library query contract."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource


def _document(
    source_id: int,
    filename: str,
    *,
    parse_status: str,
    index_status: str,
    parsed_content: str | None = None,
) -> Document:
    """Build one persisted document with deterministic metadata for query tests."""
    return Document(
        knowledge_source_id=source_id,
        file_path=filename,
        normalized_file_path=filename,
        file_hash=(filename.encode("utf-8").hex() + "0" * 64)[:64],
        file_size=len(filename),
        modified_time=datetime(2026, 8, 20, tzinfo=UTC),
        modified_time_ns=1,
        scan_state="pending",
        parse_status=parse_status,
        index_status=index_status,
        parsed_content=parsed_content,
    )


def test_document_query_filters_health_file_type_and_stably_sorts(tmp_path: Path) -> None:
    """AC-07/AC-08/AC-11: database filters run before paginating document rows."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'query.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    source_root = tmp_path / "source"
    source_root.mkdir()

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            source = KnowledgeSource(
                name="query-source",
                source_type="local_folder",
                root_path=str(source_root),
                normalized_root_path=str(source_root).casefold(),
                enabled=True,
                sync_status="idle",
            )
            session.add(source)
            await session.flush()
            session.add_all(
                [
                    _document(source.id, "zeta.pdf", parse_status="failed", index_status="outdated"),
                    _document(source.id, "alpha.pdf", parse_status="failed", index_status="outdated"),
                    _document(source.id, "ready.docx", parse_status="succeeded", index_status="succeeded"),
                ]
            )
            await session.commit()

    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/documents",
                params={
                    "health_status": "needs_attention",
                    "file_type": "pdf",
                    "sort_by": "name",
                    "sort_order": "asc",
                    "limit": 1,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["total"] == 2
            assert [item["file_path"] for item in payload["items"]] == ["alpha.pdf"]
            assert payload["items"][0]["health_status"] == "needs_attention"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_content_search_returns_real_page_or_section_locator(api_context) -> None:
    """AC-14: content mode returns locations derived from persisted parsed content."""
    client, document_id, paper = api_context
    paper.write_text("# Interstitial Lung Disease\nRelevant treatment evidence.", encoding="utf-8")
    parsed = client.post(f"/api/v1/documents/{document_id}/retry-parse")
    assert parsed.status_code == 200

    response = client.get(
        "/api/v1/documents",
        params={"mode": "content", "query": "treatment", "limit": 25},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    result = payload["items"][0]
    assert result["document_id"] == document_id
    assert result["locator_type"] in {"page", "section"}
    assert result["locator"]
    assert "treatment" in result["snippet"].casefold()
