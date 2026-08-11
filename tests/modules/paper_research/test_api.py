"""Acceptance coverage for the paper-research aggregation API."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.conversation.model import Conversation, Message
from app.modules.document.model import Document
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_analysis.prompts import FIELD_NAMES, TEMPLATE_VERSION


@pytest.fixture
def api_context(tmp_path: Path):
    """Provide an isolated API database with the production dependency override."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'paper_research.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
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

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _document(name: str, *, indexed: bool, title: str | None = None) -> Document:
    return Document(
        knowledge_source_id=1,
        file_path=name,
        normalized_file_path=name,
        file_hash=(name[0] * 64),
        file_size=1,
        modified_time=datetime.now(UTC),
        modified_time_ns=1,
        index_status="succeeded" if indexed else "failed",
        paperqa_index_key=f"idx-{name}" if indexed else None,
        parsed_title=title,
    )


async def _seed_documents(factory):
    async with factory() as session:
        local = _document("local-paper.pdf", indexed=True, title="Beta local title")
        linked = _document("linked-paper.pdf", indexed=True, title="Ignored title")
        failed = _document("failed-paper.pdf", indexed=False, title="Failed paper")
        session.add_all([local, linked, failed])
        await session.flush()
        session.add(
            LibraryItem(
                pmid="9988",
                title="Alpha traceable title",
                year=2024,
                document_id=linked.id,
                source_search_id=1,
                fulltext_status="local_pdf_available",
                fulltext_status_reason="linked for test",
            )
        )
        await session.commit()
        return local, linked, failed


def test_indexed_documents_excludes_non_successful_and_uses_traceable_metadata(
    api_context,
):
    client, factory = api_context
    asyncio.run(_seed_documents(factory))

    response = client.get("/api/v1/paper-research/indexed-documents")

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["items"]] == [
        "Alpha traceable title",
        "Beta local title",
    ]
    assert payload["items"][0]["year"] == 2024
    assert payload["items"][0]["pmid"] == "9988"
    assert payload["items"][1]["year"] is None
    assert payload["items"][1]["pmid"] is None


def test_indexed_documents_filters_and_paginates_stably(api_context):
    client, factory = api_context
    asyncio.run(_seed_documents(factory))

    filtered = client.get(
        "/api/v1/paper-research/indexed-documents", params={"q": "9988"}
    )
    paged = client.get(
        "/api/v1/paper-research/indexed-documents", params={"offset": 1, "limit": 1}
    )

    assert filtered.status_code == paged.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["pmid"] == "9988"
    assert paged.json()["total"] == 2
    assert paged.json()["items"][0]["title"] == "Beta local title"


def _structured_result() -> str:
    return json.dumps(
        {
            name: {"value": "original value", "kind": "summary", "source_indices": []}
            for name in FIELD_NAMES
        }
    )


async def _seed_overview(factory) -> tuple[int, int]:
    local, linked, _ = await _seed_documents(factory)
    async with factory() as session:
        now = datetime.now(UTC)
        analysis = PaperAnalysis(
            document_id=linked.id,
            analysis_status="succeeded",
            template_version=TEMPLATE_VERSION,
            model_version="test",
            generation=1,
            structured_result=_structured_result(),
            sources="[]",
            pending_confirmations=json.dumps(["sample_size", "limitations"]),
            created_at=now - timedelta(minutes=1),
            updated_at=now,
        )
        older = PaperAnalysis(
            document_id=local.id,
            analysis_status="succeeded",
            template_version=TEMPLATE_VERSION,
            model_version="test",
            generation=1,
            structured_result=_structured_result(),
            sources="[]",
            pending_confirmations="[]",
            created_at=now - timedelta(minutes=2),
            updated_at=now - timedelta(minutes=2),
        )
        conversation = Conversation(
            document_ids=json.dumps([linked.id]),
            title="Recent evidence question",
            created_at=now - timedelta(minutes=3),
            updated_at=now,
        )
        session.add_all([analysis, older, conversation])
        await session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                sequence=1,
                role="user",
                content="Question",
                created_at=now,
            )
        )
        await session.commit()
        return analysis.id, conversation.id


def test_overview_aggregates_recent_items_pending_fields_and_empty_state(api_context):
    client, factory = api_context
    assert client.get("/api/v1/paper-research/overview").json() == {
        "recent_analyses": [],
        "pending_confirmations": [],
        "recent_conversations": [],
    }
    analysis_id, conversation_id = asyncio.run(_seed_overview(factory))

    response = client.get("/api/v1/paper-research/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_analyses"][0]["analysis_id"] == analysis_id
    assert {item["field_name"] for item in payload["pending_confirmations"]} == {
        "sample_size",
        "limitations",
    }
    assert payload["recent_conversations"][0]["id"] == conversation_id
    assert payload["recent_conversations"][0]["message_count"] == 1


def test_existing_correction_and_delete_endpoints_remain_usable(api_context):
    client, factory = api_context
    analysis_id, conversation_id = asyncio.run(_seed_overview(factory))

    corrected = client.patch(
        f"/api/v1/paper-analysis/{analysis_id}",
        json={"field_name": "sample_size", "value": "120", "kind": "fact"},
    )
    deleted = client.delete(f"/api/v1/conversations/{conversation_id}")
    missing = client.get(f"/api/v1/conversations/{conversation_id}")

    assert corrected.status_code == 200
    assert corrected.json()["structured_result"]["sample_size"]["value"] == "120"
    assert "sample_size" not in corrected.json()["pending_confirmations"]
    assert deleted.status_code == 204
    assert missing.status_code == 404
