"""R0 云端模型手工 Smoke Test；运行一次会产生一次真实云端请求。"""

import asyncio

from app.integrations.llm import ChatMessage, LLMClient
from app.integrations.llm.exceptions import LLMClientError

TEST_MESSAGE = "Reply with exactly: cloud-llm-ok"


async def run() -> int:
    try:
        async with LLMClient.from_settings() as client:
            response = await client.chat(
                [ChatMessage(role="user", content=TEST_MESSAGE)]
            )
    except LLMClientError as error:
        print(f"Cloud LLM smoke test failed [{error.code}]: {error.message}")
        return 1

    print(f"provider={response.provider}")
    print(f"model={response.model}")
    print(f"elapsed_seconds={response.elapsed_seconds:.3f}")
    print(f"text={response.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
