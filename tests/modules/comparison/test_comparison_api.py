"""R2-WP11 comparison API lifecycle tests using the real FastAPI dependency graph."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
async def client(tmp_path):
    """Use a temporary SQLite database so lifecycle tests exercise real persistence."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'comparison.db').as_posix()}"
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

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_comparison_lifecycle_and_exports(client):
    created = client.post(
        "/api/v1/comparisons", json={"selected_document_ids": [101, 102, 103]}
    )
    assert created.status_code == 201
    task = created.json()
    assert task["selected_document_ids"] == [101, 102, 103]
    assert len(task["cells"]) == 36
    comparison_id = task["id"]

    loaded = client.get(f"/api/v1/comparisons/{comparison_id}")
    assert loaded.status_code == 200
    assert loaded.json()["id"] == comparison_id

    edited = client.patch(
        f"/api/v1/comparisons/{comparison_id}/cells",
        json={
            "document_id": 101,
            "field": "study_type",
            "user_value": "人工确认：队列研究",
        },
    )
    assert edited.status_code == 200
    edited_cell = next(
        cell
        for cell in edited.json()["cells"]
        if cell["document_id"] == 101 and cell["field"] == "study_type"
    )
    assert edited_cell["cell_value"] == "人工确认：队列研究"
    assert edited_cell["status"] == "user_edited"

    regenerated = client.post(f"/api/v1/comparisons/{comparison_id}/regenerate")
    assert regenerated.status_code == 200
    regenerated_cell = next(
        cell
        for cell in regenerated.json()["cells"]
        if cell["document_id"] == 101 and cell["field"] == "study_type"
    )
    assert regenerated_cell["cell_value"] == "人工确认：队列研究"

    csv_export = client.get(f"/api/v1/comparisons/{comparison_id}/export?format=csv")
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"].startswith("text/csv")
    assert "field,document_101,document_102,document_103" in csv_export.text
    assert "人工确认：队列研究" in csv_export.text

    markdown_export = client.get(
        f"/api/v1/comparisons/{comparison_id}/export?format=markdown"
    )
    assert markdown_export.status_code == 200
    assert markdown_export.headers["content-type"].startswith("text/markdown")
    assert "# 多论文比较" in markdown_export.text
    assert "人工确认：队列研究" in markdown_export.text
