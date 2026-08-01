"""显式启用的真实 Ollama 本地集成测试。"""

import os

import pytest

from app.integrations.llm import ChatMessage
from app.integrations.ollama import OllamaClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_TEST") != "1",
    reason="set RUN_OLLAMA_TEST=1 to run the installed local model",
)
@pytest.mark.asyncio
async def test_installed_ollama_model_returns_text():
    async with OllamaClient.from_settings() as client:
        await client.check_service()
        await client.ensure_model_available()
        response = await client.chat(
            [ChatMessage(role="user", content="Reply with exactly: ollama-local-ok")]
        )

    assert response.text
