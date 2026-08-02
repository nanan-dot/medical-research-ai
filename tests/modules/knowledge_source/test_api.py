from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    database_path = tmp_path / "api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
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

    import asyncio

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def create_source(client: TestClient, root: Path, source_type: str = "local_folder"):
    return client.post(
        "/api/v1/knowledge-sources",
        json={"name": root.name, "source_type": source_type, "root_path": str(root)},
    )


def test_crud_enable_disable_and_delete_preserves_files(client: TestClient, tmp_path: Path):
    root = tmp_path / "papers"
    root.mkdir()
    paper = root / "paper.txt"
    paper.write_text("do not delete", encoding="utf-8")

    created = create_source(client, root)
    assert created.status_code == 201
    source_id = created.json()["id"]

    duplicate = create_source(client, root, "obsidian_vault")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    disabled = client.patch(f"/api/v1/knowledge-sources/{source_id}", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    enabled = client.patch(f"/api/v1/knowledge-sources/{source_id}", json={"enabled": True})
    assert enabled.json()["enabled"] is True

    listed = client.get("/api/v1/knowledge-sources")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [source_id]

    deleted = client.delete(f"/api/v1/knowledge-sources/{source_id}")
    assert deleted.status_code == 204
    assert paper.read_text(encoding="utf-8") == "do not delete"
    assert client.get(f"/api/v1/knowledge-sources/{source_id}").status_code == 404


def test_missing_path_returns_clear_400(client: TestClient, tmp_path: Path):
    response = create_source(client, tmp_path / "missing", "temporary_import")
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_path",
        "message": "Knowledge source directory does not exist",
    }


def test_permission_and_network_errors_are_explicit(
    client: TestClient, tmp_path: Path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    monkeypatch.setattr("app.modules.knowledge_source.service.os.access", lambda *_: False)
    denied = create_source(client, root)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"

    def unavailable(*_args, **_kwargs):
        raise OSError("network share offline")

    monkeypatch.undo()
    monkeypatch.setattr(Path, "resolve", unavailable)
    response = create_source(client, root)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "temporarily_unavailable"
    assert "network share offline" not in response.text
