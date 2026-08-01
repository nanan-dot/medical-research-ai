"""显式启用后才会产生费用的真实云端模型集成测试。"""

import os

import pytest

from app.integrations.llm import ChatMessage, LLMClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_CLOUD_LLM_TEST") != "1",
    reason="set RUN_CLOUD_LLM_TEST=1 to allow one real cloud request",
)
@pytest.mark.asyncio
async def test_configured_cloud_llm_returns_text():
    async with LLMClient.from_settings() as client:
        response = await client.chat(
            [ChatMessage(role="user", content="Reply with exactly: cloud-llm-ok")]
        )

    assert response.text
