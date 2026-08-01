"""Ollama 本地适配器的无模型 Mock 测试。"""

import httpx
import pytest

from app.integrations.llm import ChatMessage
from app.integrations.ollama.client import OllamaClient
from app.integrations.ollama.exceptions import (
    OllamaConfigurationError,
    OllamaIncompatibleServiceError,
    OllamaModelNotFoundError,
    OllamaResourceError,
    OllamaResponseError,
    OllamaServiceUnavailableError,
    OllamaTimeoutError,
)

LOCAL_BASE = "http://127.0.0.1:11434"


def make_client(handler, *, model="tiny-local:latest", base_url=LOCAL_BASE):
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OllamaClient(
        base_url=base_url,
        model=model,
        timeout_seconds=1,
        http_client=http_client,
    )


def test_non_local_url_is_rejected_without_cloud_fallback():
    with pytest.raises(OllamaConfigurationError, match="local HTTP|loopback"):
        OllamaClient(base_url="https://api.openai.com", model="tiny-local:latest")


@pytest.mark.asyncio
async def test_status_models_chat_and_resources_use_only_local_host():
    requested_hosts = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.21.2"})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": "tiny-local:latest", "size": 1234}]},
            )
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(
                200,
                json={
                    "model": "tiny-local:latest",
                    "choices": [{"message": {"content": "ollama-local-ok"}}],
                },
            )
        if request.url.path == "/api/ps":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "tiny-local:latest",
                            "size": 1234,
                            "size_vram": 512,
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = make_client(handler)
    assert (await client.check_service()).version == "0.21.2"
    assert (await client.ensure_model_available()).name == "tiny-local:latest"
    response = await client.chat([ChatMessage(role="user", content="fixed local test")])
    resources = await client.get_resource_usage()
    await client._http_client.aclose()

    assert response.text == "ollama-local-ok"
    assert resources[0].size_vram_bytes == 512
    assert set(requested_hosts) == {"127.0.0.1"}


@pytest.mark.asyncio
async def test_service_closed_is_explicit_and_has_no_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = make_client(handler)
    with pytest.raises(OllamaServiceUnavailableError, match="not reachable"):
        await client.chat([ChatMessage(role="user", content="never leaves localhost")])
    await client._http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"service": "not-ollama"}, ["unexpected-version-shape"]],
)
async def test_port_occupied_by_non_ollama_service_is_rejected(payload):
    client = make_client(lambda _: httpx.Response(200, json=payload))
    with pytest.raises(OllamaIncompatibleServiceError):
        await client.check_service()
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_model_not_downloaded_is_explicit():
    client = make_client(lambda _: httpx.Response(200, json={"models": []}))
    with pytest.raises(OllamaModelNotFoundError, match="ollama pull"):
        await client.ensure_model_available()
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_model_404_is_converted():
    client = make_client(lambda _: httpx.Response(404, json={"error": "not found"}))
    with pytest.raises(OllamaModelNotFoundError):
        await client.chat([ChatMessage(role="user", content="fixed local test")])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_empty_response_is_converted():
    client = make_client(
        lambda _: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})
    )
    with pytest.raises(OllamaResponseError, match="empty"):
        await client.chat([ChatMessage(role="user", content="fixed local test")])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_first_load_timeout_is_explicit():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow first load", request=request)

    client = make_client(handler)
    with pytest.raises(OllamaTimeoutError, match="first load"):
        await client.chat([ChatMessage(role="user", content="fixed local test")])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_resource_failure_is_explicit():
    client = make_client(lambda _: httpx.Response(500, json={"error": "out of memory"}))
    with pytest.raises(OllamaResourceError, match="RAM, VRAM"):
        await client.chat([ChatMessage(role="user", content="fixed local test")])
    await client._http_client.aclose()
