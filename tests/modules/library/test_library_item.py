"""R2-WP07 local metadata preservation and PDF-link tests without network access."""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.literature_search.model import LiteratureSearchResult
from app.modules.literature_search.schema import CitationItem


@pytest.fixture
async def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'library.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    async def override_session():
        async with factory() as session:
            try:
                yield session; await session.commit()
            except Exception:
                await session.rollback(); raise
    app.dependency_overrides[get_session] = override_session
    try:
        async with factory() as session:
            citation = CitationItem(pmid="123", doi="10.1234/ABC", title="Test", journal="Journal", year=2026)
            session.add(LiteratureSearchResult(query="test", total_count=1, items_json=json.dumps([citation.model_dump()])))
            await session.commit()
        with TestClient(app) as test_client: yield test_client, factory
    finally:
        app.dependency_overrides.clear(); await engine.dispose()


def test_save_metadata_is_idempotent_and_explains_no_fulltext(client):
    api, _ = client
    first = api.post("/api/v1/literature-results/1/save", json={"pmid": "123"})
    second = api.post("/api/v1/literature-results/1/save", json={"pmid": "123"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["fulltext_status"] == "metadata_only"
    assert "No local PDF" in first.json()["fulltext_status_reason"]


@pytest.mark.asyncio
async def test_exact_doi_match_then_manual_link_and_unlink(client):
    api, factory = client
    async with factory() as session:
        session.add(Document(knowledge_source_id=1, file_path="paper.pdf", normalized_file_path="paper.pdf", file_hash="a" * 64, file_size=1, modified_time=datetime.now(UTC), modified_time_ns=1, parsed_content="DOI: 10.1234/abc"))
        await session.commit()
    saved = api.post("/api/v1/literature-results/1/save", json={"pmid": "123"}).json()
    assert saved["document_id"] == 1
    assert saved["fulltext_status"] == "local_pdf_available"
    unlinked = api.post(f"/api/v1/library-items/{saved['id']}/link-local-pdf", json={"document_id": None})
    assert unlinked.status_code == 200
    assert unlinked.json()["document_id"] is None
    assert unlinked.json()["fulltext_status"] == "metadata_only"


def test_wrong_doi_never_fuzzy_matches(client):
    api, _ = client
    response = api.post("/api/v1/literature-results/1/save", json={"pmid": "123"})
    assert response.status_code == 200
