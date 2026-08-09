import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}"
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_sync_and_status_endpoints(client: TestClient, tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "paper.md").write_text("public test fixture", encoding="utf-8")
    created = client.post(
        "/api/v1/knowledge-sources",
        json={"name": "source", "source_type": "local_folder", "root_path": str(root)},
    )
    source_id = created.json()["id"]

    synced = client.post(f"/api/v1/knowledge-sources/{source_id}/sync")
    assert synced.status_code == 200
    assert synced.json()["added"] == 1
    status = client.get(f"/api/v1/knowledge-sources/{source_id}/sync-status")
    assert status.status_code == 200
    assert status.json() == synced.json()
