"""HTTP contract checks for state, validation, and stable conflict envelopes."""

from collections.abc import AsyncIterator

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.common.exception_handlers import app_error_handler
from app.common.exceptions import AppError
from app.core.database import get_session
from app.modules.note_library.router import router


async def test_nb19_http_contract_and_nb20_conflict_envelope(note_factory):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router, prefix="/api/v1")

    async def session_override() -> AsyncIterator[object]:
        async with note_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = session_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/note-library/notes", json={"actor_scope": "user:http"}
        )
        assert created.status_code == 201
        note_id = created.json()["id"]
        saved = await client.put(
            f"/api/v1/note-library/notes/{note_id}/draft",
            json={
                "actor_scope": "user:http",
                "expected_draft_version": 1,
                "title": "Title",
                "body": "Body",
                "sources": [],
            },
        )
        assert saved.json()["save_state"] == "draft_saved"
        conflict = await client.put(
            f"/api/v1/note-library/notes/{note_id}/draft",
            headers={"X-Request-ID": "request-test"},
            json={
                "actor_scope": "user:http",
                "expected_draft_version": 1,
                "title": "stale",
                "body": "stale",
                "sources": [],
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"] == {
            "code": "NOTE_DRAFT_VERSION_CONFLICT",
            "message": "Draft version has changed",
            "request_id": "request-test",
        }
        invalid = await client.get(
            "/api/v1/note-library/notes",
            params={"actor_scope": "user:http", "page_size": 21},
        )
        assert invalid.status_code == 422


async def test_ai_completion_is_not_a_public_note_library_route(note_factory):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session_override() -> AsyncIterator[object]:
        async with note_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/note-library/ai-suggestions/1/complete", json={}
        )

    assert response.status_code == 404
