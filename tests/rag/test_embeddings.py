"""Embedding 客户端测试（dummy 确定性 + ollama 本地 mock）。"""

import json

import httpx
import pytest

from app.rag.embeddings import (
    DummyEmbeddingClient,
    EmbeddingDimensionError,
    EmbeddingError,
    OllamaEmbeddingClient,
    create_embedding_client,
)

LOCAL_BASE = "http://127.0.0.1:11434"


def make_ollama(handler, *, model="nomic-embed-text"):
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OllamaEmbeddingClient(
        base_url=LOCAL_BASE,
        model=model,
        timeout_seconds=1,
        http_client=http_client,
    )


def _mock_embed_handler(dimension: int = 4):
    def handler(request: httpx.Request) -> httpx.Response:
        # httpx.Request 没有 .json()，需从字节内容解析。
        payload = json.loads(request.content)
        texts = payload["input"]
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "embeddings": [[float(index) + 1.0 for index in range(dimension)] for _ in texts],
            },
        )

    return handler


@pytest.mark.asyncio
async def test_dummy_embedding_is_deterministic_and_fixed_dimension():
    client = DummyEmbeddingClient(dimension=16)
    first = await client.embed(["你好"])
    second = await client.embed(["你好"])
    assert first == second
    assert len(first[0]) == 16


@pytest.mark.asyncio
async def test_dummy_embedding_handles_chinese_and_english_same_dimension():
    client = DummyEmbeddingClient(dimension=16)
    vectors = await client.embed(["你好，世界", "EGFR resistance"])
    assert len(vectors) == 2
    assert all(len(vector) == 16 for vector in vectors)


def test_dummy_embedding_invalid_dimension_is_rejected():
    with pytest.raises(EmbeddingError, match="positive"):
        DummyEmbeddingClient(dimension=0)


@pytest.mark.asyncio
async def test_ollama_embedding_returns_expected_dimension():
    client = make_ollama(_mock_embed_handler(dimension=4))
    vectors = await client.embed(["EGFR 耐药", "resistance"])
    assert len(vectors) == 2
    assert all(len(vector) == 4 for vector in vectors)
    assert client.dimension == 4
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_ollama_unreachable_is_explicit():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = make_ollama(handler)
    with pytest.raises(EmbeddingError, match="unreachable"):
        await client.embed(["text"])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_ollama_empty_embeddings_are_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "m", "embeddings": []})

    client = make_ollama(handler)
    with pytest.raises(EmbeddingError, match="incompatible"):
        await client.embed(["text"])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_ollama_declared_dimension_mismatch_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "m",
                "embeddings": [[1.0, 2.0, 3.0]],
            },
        )

    client = make_ollama(handler)
    # 声明维度与实际响应不一致 → 明确报错而不是静默截断
    client._declared_dimension = 4
    with pytest.raises(EmbeddingDimensionError, match="does not match"):
        await client.embed(["text"])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_ollama_non_loopback_url_is_rejected():
    # 校验消息为 "must be a local HTTP URL"（见 _validate_local_base_url）。
    with pytest.raises(EmbeddingError, match="local HTTP URL"):
        OllamaEmbeddingClient(
            base_url="https://api.example.com",
            model="m",
        )


def test_create_embedding_client_supports_dummy_and_ollama():
    dummy = create_embedding_client(
        provider="dummy",
        base_url="http://127.0.0.1:11434",
        model="nomic-embed-text",
        dimension=16,
    )
    assert isinstance(dummy, DummyEmbeddingClient)

    ollama = create_embedding_client(
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        model="nomic-embed-text",
    )
    assert isinstance(ollama, OllamaEmbeddingClient)


def test_create_embedding_client_rejects_unknown_provider():
    with pytest.raises(EmbeddingError, match="unsupported"):
        create_embedding_client(
            provider="cloud",
            base_url="http://127.0.0.1:11434",
            model="m",
        )
