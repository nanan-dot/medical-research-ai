import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource


@pytest.fixture
def navigation_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.modules.document_navigation import service as navigation_service

    # 本机 .env 可启用真实重排；接口测试默认隔离运行时模型配置。
    monkeypatch.setattr(
        navigation_service.settings, "NAVIGATION_RERANK_ENABLED", False
    )
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'navigation.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> tuple[int, int]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            source = KnowledgeSource(name="肿瘤资料", source_type="local_folder", root_path=str(tmp_path), normalized_root_path=str(tmp_path).casefold(), enabled=True, sync_status="idle")
            other = KnowledgeSource(name="其他资料", source_type="local_folder", root_path=str(tmp_path / "other"), normalized_root_path=str(tmp_path / "other").casefold(), enabled=True, sync_status="idle")
            session.add_all([source, other]); await session.flush()
            now = datetime.now(UTC)
            parsed = '{"source_path":"liver.pdf","title":"肝癌 PD-1 研究","text":"PD-1 联合治疗讨论耐药机制。","pages":[{"page_number":7,"text":"PD-1 联合治疗讨论耐药机制。"}],"sections":[{"heading":"耐药机制","level":2,"text":"PD-1 联合治疗讨论耐药机制。"}]}'
            eligible = Document(knowledge_source_id=source.id, file_path="trials/liver.pdf", normalized_file_path="trials/liver.pdf", file_hash="a" * 64, file_size=1, modified_time=now, modified_time_ns=1, scan_state="pending", parse_status="succeeded", index_status="succeeded", paperqa_index_key="index-1", parsed_content=parsed)
            unindexed = Document(knowledge_source_id=other.id, file_path="other.pdf", normalized_file_path="other.pdf", file_hash="b" * 64, file_size=1, modified_time=now, modified_time_ns=2, scan_state="pending", parse_status="succeeded", index_status="pending", parsed_content=parsed)
            session.add_all([eligible, unindexed]); await session.commit()
            return source.id, other.id

    async def override_session():
        async with factory() as session:
            try:
                yield session; await session.commit()
            except Exception:
                await session.rollback(); raise

    source_id, other_id = asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, source_id, other_id
    app.dependency_overrides.clear(); asyncio.run(engine.dispose())


def test_navigation_returns_real_source_page_and_excerpt(navigation_client):
    client, source_id, _ = navigation_client
    response = client.post("/api/v1/document-navigation/search", json={"query": "PD-1 耐药机制", "knowledge_source_id": source_id, "indexed_only": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["searchable_document_count"] == 1
    assert payload["results"][0]["knowledge_source_name"] == "肿瘤资料"
    assert payload["results"][0]["relative_path"] == "trials/liver.pdf"
    assert payload["results"][0]["location"]["page_number"] == 7
    assert "耐药机制" in payload["results"][0]["excerpt"]
    assert payload["strategy"] == "bm25"


def test_navigation_uses_hybrid_when_local_vector_is_available(navigation_client, monkeypatch):
    from app.modules.document_navigation import service as navigation_service

    class LocalEmbedding:
        model_name = "local-test"
        dimension = 2

        async def embed(self, texts):
            return [[float(len(text) % 3), 1.0] for text in texts]

    monkeypatch.setattr(navigation_service.settings, "EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setattr(navigation_service, "create_embedding_client", lambda **_: LocalEmbedding())
    client, _, _ = navigation_client
    response = client.post("/api/v1/document-navigation/search", json={"query": "PD-1", "indexed_only": True})
    assert response.status_code == 200
    assert response.json()["strategy"] == "hybrid"
    assert response.json()["results"][0]["retrieval_score"] is not None


def test_navigation_empty_and_index_scope(navigation_client):
    client, _, other_id = navigation_client
    empty = client.post("/api/v1/document-navigation/search", json={"query": "不存在的术语", "indexed_only": True})
    assert empty.status_code == 200 and empty.json()["results"] == []
    excluded = client.post("/api/v1/document-navigation/search", json={"query": "PD-1", "knowledge_source_id": other_id, "indexed_only": True})
    assert excluded.status_code == 200
    assert excluded.json()["searchable_document_count"] == 0
    included = client.post("/api/v1/document-navigation/search", json={"query": "PD-1", "knowledge_source_id": other_id, "indexed_only": False})
    assert included.status_code == 200
    assert included.json()["searchable_document_count"] == 0


def test_navigation_condition_is_not_claimed_without_source_proof(navigation_client):
    client, _, _ = navigation_client
    response = client.post("/api/v1/document-navigation/search", json={"query": "近三年 随机对照试验 PD-1", "indexed_only": True})
    assert response.status_code == 200
    statuses = response.json()["results"][0]["condition_status"]
    assert {item["status"] for item in statuses} == {"unverified"}


def test_navigation_validates_request(navigation_client):
    client, _, _ = navigation_client
    assert client.post("/api/v1/document-navigation/search", json={"query": ""}).status_code == 422
