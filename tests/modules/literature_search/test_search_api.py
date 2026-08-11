"""literature_search 检索执行与 BibTeX 导出 API 测试。

通过替换 service 的 pubmed_executor 为替身避免真实网络，同时用临时 SQLite
覆盖 get_session 依赖，确保不写入开发库。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.integrations.pubmed.exceptions import PubMedConnectionError
from app.main import app


class _FakeExecutor:
    """替身执行器：返回固定的带 verified 标记条目。"""

    async def execute(self, query: str, *, retmax: int = 20):
        from app.modules.literature_search.schema import CitationItem

        item = CitationItem(
            pmid="39000401",
            doi="10.1016/j.example.2024.01.001",
            title="Validation of neural networks in mammography",
            authors=["Kim J"],
            journal="Nature Medicine",
            year=2024,
            verified=True,
            verified_by="pubmed",
            verified_on="2026-08-05T00:00:00+00:00",
        )
        return [item], 1


class _UnavailableExecutor:
    async def execute(self, query: str, *, retmax: int = 20):
        raise PubMedConnectionError("Could not reach NCBI after 3 attempts")


@pytest.fixture
async def client(tmp_path: Path, monkeypatch):
    from app.modules.literature_search.service import LiteratureSearchService

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'litsearch.db').as_posix()}"
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

    original_init = LiteratureSearchService.__init__

    def patched_init(
        self,
        session,
        *,
        candidate_extractor=None,
        mesh_client=None,
        pubmed_executor=None,
    ):
        original_init(
            self,
            session,
            candidate_extractor=candidate_extractor,
            mesh_client=mesh_client,
            pubmed_executor=_FakeExecutor(),
        )

    monkeypatch.setattr(LiteratureSearchService, "__init__", patched_init)
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_execute_and_bibtex_flow(client):
    created = client.post(
        "/api/v1/literature-search/execute",
        json={"boolean_query": '"neural networks" AND "mammography"', "retmax": 5},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["total_count"] == 1
    assert payload["items"][0]["verified"] is True
    assert payload["items"][0]["verified_by"] == "pubmed"

    result_id = payload["id"]
    bibtex = client.get(f"/api/v1/literature-search/{result_id}/bibtex")
    assert bibtex.status_code == 200
    assert bibtex.headers["content-type"].startswith("text/plain")
    assert "@article{Kim_2024_Validation," in bibtex.text
    assert "verified = {true}," in bibtex.text
    assert "verified_by = {pubmed}," in bibtex.text


def test_results_endpoint_returns_persisted_items(client):
    created = client.post(
        "/api/v1/literature-search/execute",
        json={"boolean_query": "cancer immunotherapy", "retmax": 3},
    )
    result_id = created.json()["id"]

    # R2-WP05 起 GET /{id}/results 返回分页响应：items 为带排序理由的条目。
    loaded = client.get(f"/api/v1/literature-search/{result_id}/results")
    assert loaded.status_code == 200
    payload = loaded.json()
    assert payload["items"][0]["item"]["pmid"] == "39000401"
    assert payload["sort"] == "relevance"
    assert payload["page"] == 1
    assert payload["filtered_total"] == 1


def test_bibtex_for_missing_result_returns_404(client):
    response = client.get("/api/v1/literature-search/99999/bibtex")
    assert response.status_code == 404


def test_execute_returns_service_unavailable_when_pubmed_cannot_be_reached(
    client, monkeypatch
):
    monkeypatch.setattr(_FakeExecutor, "execute", _UnavailableExecutor.execute)
    response = client.post(
        "/api/v1/literature-search/execute",
        json={"boolean_query": "cancer immunotherapy", "retmax": 1},
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "pubmed_connection_error",
            "message": "Could not reach NCBI after 3 attempts",
        }
    }
