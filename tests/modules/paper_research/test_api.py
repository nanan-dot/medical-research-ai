"""Acceptance coverage for the paper-research aggregation API."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError
from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.conversation.model import Conversation, Message
from app.modules.document.model import Document
from app.modules.document_reader.model import ReaderSession
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_analysis.prompts import FIELD_NAMES, TEMPLATE_VERSION
from app.modules.paper_library.model import (
    PaperActivity,
    PaperLibraryMember,
    PaperResearchCenterPreference,
    PaperResearchRelation,
    PaperWorkState,
)
from app.modules.paper_research.center_schema import (
    CurrentContextStageUpdate,
    CurrentContextUpdate,
)
from app.modules.paper_research.center_service import CenterService
from app.modules.research_context.model import ResearchContext


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


def test_center_empty_contract_and_limit_validation(api_context):
    client, _ = api_context
    response = client.get("/api/v1/paper-research/center")
    assert response.status_code == 200
    assert response.json() == {
        "current_research": None,
        "continue_tasks": [],
        "recent_activities": [],
        "recent_papers": [],
        "summary": {
            "papers": 0,
            "reading": 0,
            "deep_reading": 0,
            "completed": 0,
            "pending_confirmation_items": 0,
            "pending_confirmation_fields": 0,
        },
        "capabilities": {
            "current_research_selection": "available",
            "exact_reader_resume": "available",
            "next_action_rules": "available",
            "ai_task_planning": "unavailable",
        },
    }
    assert (
        client.get(
            "/api/v1/paper-research/center", params={"continue_limit": 0}
        ).status_code
        == 422
    )


async def _seed_context(factory) -> int:
    async with factory() as session:
        context = ResearchContext(name="Evidence synthesis", description="")
        session.add(context)
        await session.commit()
        return context.id


def test_current_context_is_explicit_versioned_and_clearable(api_context):
    client, factory = api_context
    context_id = asyncio.run(_seed_context(factory))
    created = client.put(
        "/api/v1/paper-research/current-context",
        json={
            "research_context_id": context_id,
            "stage": "literature_reading",
            "expected_version": 1,
        },
    )
    assert created.status_code == 200
    assert created.json()["research_context_id"] == context_id
    assert created.json()["version"] == 1
    updated = client.patch(
        "/api/v1/paper-research/current-context/stage",
        json={"stage": "paper_understanding", "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["stage"] == "paper_understanding"
    conflict = client.patch(
        "/api/v1/paper-research/current-context/stage",
        json={"stage": "conclusion_formation", "expected_version": 1},
    )
    assert conflict.status_code == 409
    cleared = client.put(
        "/api/v1/paper-research/current-context",
        json={
            "research_context_id": None,
            "stage": "problem_definition",
            "expected_version": 2,
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["research_context_id"] is None
    assert (
        client.put(
            "/api/v1/paper-research/current-context",
            json={
                "research_context_id": 99999,
                "stage": "literature_reading",
                "expected_version": 3,
            },
        ).status_code
        == 404
    )


async def _seed_center_data(factory) -> tuple[int, int, int]:
    async with factory() as session:
        now = datetime.now(UTC)
        first = _document("center-first.pdf", indexed=True, title="First")
        second = _document("center-second.pdf", indexed=True, title="Second")
        context = ResearchContext(name="Center context", description="")
        session.add_all([first, second, context])
        await session.flush()
        first_item = LibraryItem(
            title="First paper",
            document_id=first.id,
            fulltext_status="local_pdf_available",
            fulltext_status_reason="test",
        )
        second_item = LibraryItem(
            title="Second paper",
            document_id=second.id,
            fulltext_status="metadata_only",
            fulltext_status_reason="test",
        )
        session.add_all([first_item, second_item])
        await session.flush()
        session.add_all(
            [
                PaperLibraryMember(library_item_id=first_item.id, import_source="test"),
                PaperLibraryMember(
                    library_item_id=second_item.id, import_source="test"
                ),
                PaperWorkState(
                    library_item_id=first_item.id,
                    reading_status="reading",
                    reading_progress_percent=40,
                    current_section="Methods",
                    last_read_at=now,
                ),
                PaperWorkState(
                    library_item_id=second_item.id,
                    reading_status="reading",
                    reading_progress_percent=60,
                    last_read_at=now,
                ),
                PaperResearchRelation(
                    library_item_id=first_item.id,
                    research_context_id=context.id,
                    role="core",
                ),
                PaperActivity(
                    library_item_id=first_item.id,
                    actor_scope="actor:a",
                    kind="reading_progressed",
                    detail="progress",
                    created_at=now,
                ),
                PaperActivity(
                    library_item_id=second_item.id,
                    actor_scope="actor:b",
                    kind="reading_progressed",
                    detail="other",
                    created_at=now,
                ),
            ]
        )
        await session.commit()
        return first_item.id, second_item.id, context.id


def test_center_projects_capabilities_context_isolation_and_activity_scope(api_context):
    _, factory = api_context
    first_item_id, second_item_id, context_id = asyncio.run(_seed_center_data(factory))

    async def project():
        async with factory() as session:
            service = CenterService(session, actor_scope="actor:a")
            await service.set_context(
                CurrentContextUpdate(
                    research_context_id=context_id,
                    stage="literature_reading",
                    expected_version=1,
                )
            )
            await session.commit()
        async with factory() as session:
            return await CenterService(session, actor_scope="actor:a").center(
                10, 10, 10
            )

    payload = asyncio.run(project())
    assert [task.paper_item_id for task in payload.continue_tasks] == [first_item_id]
    assert payload.continue_tasks[0].next_action.kind == "continue_reading"
    assert payload.continue_tasks[0].next_action.target == {
        "item_id": first_item_id,
        "section": "Methods",
    }
    assert [activity.paper_item_id for activity in payload.recent_activities] == [
        first_item_id
    ]
    assert second_item_id not in [
        paper.paper_item_id for paper in payload.recent_papers
    ]

    async def other_actor_context():
        async with factory() as session:
            return await CenterService(session, actor_scope="actor:b").current_context()

    assert asyncio.run(other_actor_context()) is None


def test_current_context_compare_and_swap_uses_independent_sessions(api_context):
    _, factory = api_context
    asyncio.run(_seed_context(factory))

    async def race() -> tuple[str, str]:
        async with factory() as setup:
            await CenterService(setup).set_context(
                CurrentContextUpdate(
                    research_context_id=None,
                    stage="problem_definition",
                    expected_version=1,
                )
            )
            await setup.commit()
        async with factory() as left, factory() as right:

            async def update(session, stage: str) -> str:
                try:
                    await CenterService(session).update_stage(
                        CurrentContextStageUpdate(stage=stage, expected_version=1)
                    )
                    await session.commit()
                    return "success"
                except ConflictError:
                    await session.rollback()
                    return "conflict"

            results = await asyncio.gather(
                update(left, "literature_reading"),
                update(right, "paper_understanding"),
            )
        return tuple(sorted(results))

    assert asyncio.run(race()) == ("conflict", "success")


def test_reader_resume_uses_latest_valid_session_and_degrades_on_hash_change(
    api_context,
):
    _, factory = api_context
    item_id, _, _ = asyncio.run(_seed_center_data(factory))

    async def project() -> tuple[dict[str, object] | None, dict[str, object] | None]:
        async with factory() as session:
            item = await session.get(LibraryItem, item_id)
            document = await session.get(Document, item.document_id)
            now = datetime.now(UTC)
            session.add_all(
                [
                    ReaderSession(
                        actor_scope="actor:a",
                        library_item_id=item_id,
                        document_id=document.id,
                        document_file_hash=document.file_hash,
                        device_id="test",
                        last_page=3,
                        viewport_offset_ratio=0.2,
                        last_seen_at=now - timedelta(minutes=1),
                    ),
                    ReaderSession(
                        actor_scope="actor:a",
                        library_item_id=item_id,
                        document_id=document.id,
                        document_file_hash=document.file_hash,
                        device_id="test",
                        last_page=8,
                        viewport_offset_ratio=0.8,
                        last_seen_at=now,
                    ),
                    ReaderSession(
                        actor_scope="actor:a",
                        library_item_id=item_id,
                        document_id=document.id,
                        document_file_hash=document.file_hash,
                        device_id="test",
                        last_page=9,
                        viewport_offset_ratio=0.9,
                        last_seen_at=now + timedelta(minutes=1),
                        is_history_hidden=True,
                    ),
                ]
            )
            await session.commit()
        async with factory() as session:
            exact = (
                (await CenterService(session, "actor:a").center(10, 10, 10))
                .continue_tasks[0]
                .next_action.target
            )
        async with factory() as session:
            document = await session.get(
                Document, (await session.get(LibraryItem, item_id)).document_id
            )
            document.file_hash = "z" * 64
            await session.commit()
        async with factory() as session:
            fallback = (
                (await CenterService(session, "actor:a").center(10, 10, 10))
                .continue_tasks[0]
                .next_action.target
            )
        return exact, fallback

    exact, fallback = asyncio.run(project())
    assert exact is not None and exact["page"] == 8 and exact["offset"] == 0.8
    assert fallback == {"item_id": item_id, "section": "Methods"}


def test_activity_cursor_same_timestamp_is_stable_and_actor_scoped(api_context):
    _, factory = api_context
    item_id, _, _ = asyncio.run(_seed_center_data(factory))

    async def page_ids() -> tuple[list[int], list[int], list[int]]:
        async with factory() as session:
            stamp = datetime.now(UTC)
            session.add_all(
                [
                    PaperActivity(
                        library_item_id=item_id,
                        actor_scope="actor:a",
                        kind="analysis_started",
                        created_at=stamp,
                    ),
                    PaperActivity(
                        library_item_id=item_id,
                        actor_scope="actor:a",
                        kind="analysis_progressed",
                        created_at=stamp,
                    ),
                    PaperActivity(
                        library_item_id=item_id,
                        actor_scope="actor:b",
                        kind="analysis_completed",
                        created_at=stamp,
                    ),
                ]
            )
            await session.commit()
        async with factory() as session:
            service = CenterService(session, "actor:a")
            first = await service.activity_page(None, 2)
            second = await service.activity_page(first.next_cursor, 2)
            other = await CenterService(session, "actor:b").activity_page(None, 10)
            return (
                [item.id for item in first.items],
                [item.id for item in second.items],
                [item.id for item in other.items],
            )

    first, second, other = asyncio.run(page_ids())
    assert len(first) == 2
    assert not set(first).intersection(second)
    assert len(first + second) == 3
    assert len(other) == 2


def test_activity_invalid_cursor_returns_structured_validation_error(api_context):
    client, _ = api_context
    response = client.get("/api/v1/paper-research/activities", params={"cursor": "%%%"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unprocessable_entity"


def test_center_query_budget_is_constant_and_sorting_is_stable_for_500_candidates(
    api_context,
):
    _, factory = api_context

    async def add_candidates(count: int) -> None:
        async with factory() as session:
            items = [
                LibraryItem(
                    title=f"Candidate {index:03d}",
                    fulltext_status="metadata_only",
                    fulltext_status_reason="test",
                )
                for index in range(count)
            ]
            session.add_all(items)
            await session.flush()
            session.add_all(
                PaperLibraryMember(library_item_id=item.id, import_source="test")
                for item in items
            )
            await session.commit()

    async def measured_ids() -> tuple[int, list[int], list[int]]:
        statements: list[str] = []

        def record(*args) -> None:
            statements.append(args[2])

        event.listen(factory.kw["bind"].sync_engine, "before_cursor_execute", record)
        try:
            async with factory() as session:
                first = await CenterService(session).center(10, 5, 5)
                second = await CenterService(session).center(10, 5, 5)
        finally:
            event.remove(
                factory.kw["bind"].sync_engine, "before_cursor_execute", record
            )
        return (
            len(statements) // 2,
            [task.paper_item_id for task in first.continue_tasks],
            [task.paper_item_id for task in second.continue_tasks],
        )

    asyncio.run(add_candidates(1))
    one_queries, _, _ = asyncio.run(measured_ids())
    asyncio.run(add_candidates(499))
    five_hundred_queries, first_ids, second_ids = asyncio.run(measured_ids())
    assert five_hundred_queries == one_queries
    assert first_ids == second_ids == sorted(first_ids)


def test_center_summary_uses_latest_analysis_and_distinguishes_pending_items_fields(
    api_context,
):
    _, factory = api_context

    async def project() -> dict[str, int]:
        async with factory() as session:
            now = datetime.now(UTC)
            documents = [
                _document(f"summary-{index}.pdf", indexed=True) for index in range(3)
            ]
            session.add_all(documents)
            await session.flush()
            items = [
                LibraryItem(
                    document_id=document.id,
                    title=f"Summary {index}",
                    fulltext_status="local_pdf_available",
                    fulltext_status_reason="test",
                )
                for index, document in enumerate(documents)
            ]
            session.add_all(items)
            await session.flush()
            session.add_all(
                [
                    *(
                        PaperLibraryMember(
                            library_item_id=item.id, import_source="test"
                        )
                        for item in items
                    ),
                    PaperWorkState(
                        library_item_id=items[0].id,
                        reading_status="reading",
                        reading_progress_percent=10,
                    ),
                    PaperWorkState(
                        library_item_id=items[1].id,
                        reading_status="read",
                        reading_progress_percent=100,
                    ),
                    PaperWorkState(
                        library_item_id=items[2].id,
                        reading_status="read",
                        reading_progress_percent=100,
                    ),
                    PaperAnalysis(
                        document_id=documents[0].id,
                        analysis_status="succeeded",
                        template_version="test",
                        model_version="test",
                        generation=1,
                        pending_confirmations=json.dumps(["a", "b"]),
                        created_at=now,
                        updated_at=now,
                    ),
                    PaperAnalysis(
                        document_id=documents[1].id,
                        analysis_status="analyzing",
                        template_version="test",
                        model_version="test",
                        generation=1,
                        pending_confirmations="[]",
                        created_at=now,
                        updated_at=now,
                    ),
                    PaperAnalysis(
                        document_id=documents[2].id,
                        analysis_status="pending",
                        template_version="test",
                        model_version="test",
                        generation=1,
                        pending_confirmations="[]",
                        created_at=now,
                        updated_at=now,
                    ),
                    PaperAnalysis(
                        document_id=documents[2].id,
                        analysis_status="succeeded",
                        template_version="test",
                        model_version="test",
                        generation=2,
                        pending_confirmations=json.dumps(["c"]),
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
            await session.commit()
        async with factory() as session:
            return (
                await CenterService(session).center(10, 10, 10)
            ).summary.model_dump()

    assert asyncio.run(project()) == {
        "papers": 3,
        "reading": 1,
        "deep_reading": 1,
        "completed": 1,
        "pending_confirmation_items": 2,
        "pending_confirmation_fields": 3,
    }


def test_failed_cancelled_and_unknown_analysis_never_forge_progress_or_completion(
    api_context,
):
    _, factory = api_context

    async def project():
        async with factory() as session:
            now = datetime.now(UTC)
            documents = [
                _document(f"resilient-{index}.pdf", indexed=True) for index in range(3)
            ]
            session.add_all(documents)
            await session.flush()
            items = [
                LibraryItem(
                    document_id=document.id,
                    title=f"Resilient {index}",
                    fulltext_status="metadata_only",
                    fulltext_status_reason="resource unavailable",
                )
                for index, document in enumerate(documents)
            ]
            session.add_all(items)
            await session.flush()
            session.add_all(
                [
                    *(
                        PaperLibraryMember(
                            library_item_id=item.id, import_source="test"
                        )
                        for item in items
                    ),
                    *(
                        PaperWorkState(
                            library_item_id=item.id,
                            reading_status="reading",
                            reading_progress_percent=25,
                        )
                        for item in items
                    ),
                    *(
                        PaperAnalysis(
                            document_id=document.id,
                            analysis_status=status,
                            template_version="test",
                            model_version="test",
                            generation=1,
                            task_names_json="not-json" if status == "failed" else None,
                            completed_task_names_json=None,
                            pending_confirmations=None,
                            created_at=now,
                            updated_at=now,
                        )
                        for document, status in zip(
                            documents, ("failed", "cancelled", "unknown"), strict=True
                        )
                    ),
                ]
            )
            await session.commit()
        async with factory() as session:
            return await CenterService(session).center(10, 10, 10)

    center = asyncio.run(project())
    assert center.summary.completed == 0
    assert center.summary.deep_reading == 0
    assert all(task.analysis_total == 0 for task in center.continue_tasks)
    assert all(not task.entry_available for task in center.continue_tasks)
    assert all(task.next_action.target is None for task in center.continue_tasks)


def test_center_get_is_read_only_and_openapi_contract_is_typed(api_context):
    client, factory = api_context

    async def preference_count() -> int:
        async with factory() as session:
            return int(
                await session.scalar(
                    select(func.count(PaperResearchCenterPreference.id))
                )
                or 0
            )

    before = asyncio.run(preference_count())
    response = client.get("/api/v1/paper-research/center")
    after = asyncio.run(preference_count())
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/paper-research/center"
    ]["get"]
    assert response.status_code == 200
    assert before == after == 0
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CenterRead"
    }
