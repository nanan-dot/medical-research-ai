"""统一任务中心 API 回归测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
async def client(tmp_path):
    """使用临时 SQLite 数据库验证真实 API 持久化链路。"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'tasks.db').as_posix()}"
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


def test_create_list_filter_and_get_task(client: TestClient) -> None:
    """新建任务可被分页读取，并保留创建时的来源上下文。"""
    created = client.post(
        "/api/v1/tasks",
        json={
            "task_type": "paper_analysis",
            "title": "分析文档 12",
            "source_type": "document",
            "source_id": 12,
            "detail": {"document_name": "example.pdf"},
        },
    )

    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "pending"
    assert task["progress"] == 0
    assert task["detail"] == {"document_name": "example.pdf"}

    listed = client.get("/api/v1/tasks?status=pending")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == task["id"]

    loaded = client.get(f"/api/v1/tasks/{task['id']}")
    assert loaded.status_code == 200
    assert loaded.json()["source_id"] == 12


def test_get_missing_task_returns_not_found(client: TestClient) -> None:
    """不存在的任务不能被伪装成空成功响应。"""
    response = client.get("/api/v1/tasks/999")

    assert response.status_code == 404
