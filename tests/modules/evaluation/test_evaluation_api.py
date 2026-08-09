import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
async def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'evaluation.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    async def override_session():
        async with factory() as session:
            yield session
            await session.commit()
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client: yield test_client
    finally:
        app.dependency_overrides.clear(); await engine.dispose()

def test_create_read_and_empty_results(client: TestClient) -> None:
    created = client.post("/api/v1/evaluations", json={"dataset_version":"v1","prompt_version":"p1","retriever_config":{"top_k":5},"model_config":{"name":"local"}})
    assert created.status_code == 201
    run = created.json(); assert run["status"] == "pending"
    assert client.get(f"/api/v1/evaluations/{run['id']}").status_code == 200
    assert client.get(f"/api/v1/evaluations/{run['id']}/results").json() == []
    result = client.post(f"/api/v1/evaluations/{run['id']}/results", json={"question_id":"q1","status":"completed","raw_output":"output","elapsed_ms":10})
    assert result.status_code == 201
    assert client.get(f"/api/v1/evaluations/{run['id']}/results").json()[0]["question_id"] == "q1"

def test_missing_run_is_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/evaluations/999").status_code == 404
