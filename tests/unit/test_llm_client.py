"""统一云端模型客户端的无费用 Mock 测试。"""

import logging

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseFormatError,
    LLMTimeoutError,
)
from app.integrations.llm.schemas import ChatMessage, LLMConfig

API_KEY = "unit-test-secret-key"


def make_config() -> LLMConfig:
    return LLMConfig(
        provider="mock-provider",
        model="mock-model",
        api_base="https://llm.example.test/v1",
        api_key=SecretStr(API_KEY),
        timeout_seconds=1,
    )


def make_client(handler) -> LLMClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return LLMClient(config=make_config(), http_client=http_client)


def test_from_settings_requires_supported_cloud_provider():
    app_settings = Settings(DEFAULT_MODEL_PROVIDER="ollama")

    with pytest.raises(LLMConfigurationError, match="not enabled"):
        LLMClient.from_settings(app_settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"OPENAI_API_KEY": "", "OPENAI_MODEL": "mock-model"},
        {"OPENAI_API_KEY": API_KEY, "OPENAI_MODEL": ""},
        {
            "OPENAI_API_KEY": API_KEY,
            "OPENAI_MODEL": "mock-model",
            "OPENAI_BASE_URL": "not-a-url",
        },
    ],
)
def test_from_settings_rejects_incomplete_or_invalid_configuration(overrides):
    app_settings = Settings(**overrides)

    with pytest.raises(LLMConfigurationError):
        LLMClient.from_settings(app_settings)


@pytest.mark.asyncio
async def test_chat_returns_non_empty_text_and_elapsed_time(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://llm.example.test/v1/chat/completions"
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        return httpx.Response(
            200,
            json={
                "model": "mock-model-2026",
                "choices": [
                    {"message": {"role": "assistant", "content": " cloud-llm-ok "}}
                ],
            },
        )

    client = make_client(handler)
    with caplog.at_level(logging.INFO):
        response = await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()

    assert response.text == "cloud-llm-ok"
    assert response.model == "mock-model-2026"
    assert response.elapsed_seconds >= 0
    assert API_KEY not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (401, LLMAuthenticationError),
        (403, LLMAuthenticationError),
        (404, LLMModelNotFoundError),
        (429, LLMRateLimitError),
    ],
)
async def test_http_errors_are_converted_without_leaking_key(
    status_code, exception_type, caplog
):
    client = make_client(lambda _: httpx.Response(status_code, json={"error": API_KEY}))

    with caplog.at_level(logging.WARNING), pytest.raises(exception_type) as captured:
        await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()

    assert API_KEY not in str(captured.value)
    assert API_KEY not in caplog.text


@pytest.mark.asyncio
async def test_other_provider_error_is_safe():
    client = make_client(
        lambda _: httpx.Response(500, text=f"provider echoed {API_KEY}")
    )

    with pytest.raises(LLMProviderError, match="HTTP 500") as captured:
        await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()

    assert API_KEY not in str(captured.value)


@pytest.mark.asyncio
async def test_timeout_is_converted():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = make_client(handler)
    with pytest.raises(LLMTimeoutError, match="timed out"):
        await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()


@pytest.mark.asyncio
async def test_proxy_or_api_base_connection_error_is_converted():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ProxyError("proxy unavailable", request=request)

    client = make_client(handler)
    with pytest.raises(LLMConnectionError, match="Could not connect"):
        await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"output": "changed format"},
        {"choices": []},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
async def test_incompatible_or_empty_response_is_rejected(payload):
    client = make_client(lambda _: httpx.Response(200, json=payload))

    with pytest.raises(LLMResponseFormatError):
        await client.chat([ChatMessage(role="user", content="fixed test")])
    await client._http_client.aclose()
