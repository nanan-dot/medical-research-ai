"""R0 Ollama 本地模型 Smoke Test。"""

import asyncio

from app.integrations.llm import ChatMessage
from app.integrations.ollama import OllamaClient
from app.integrations.ollama.exceptions import OllamaError

TEST_MESSAGE = "Reply with exactly: ollama-local-ok"


async def run() -> int:
    try:
        async with OllamaClient.from_settings() as client:
            status = await client.check_service()
            model = await client.ensure_model_available()
            first = await client.chat([ChatMessage(role="user", content=TEST_MESSAGE)])
            second = await client.chat([ChatMessage(role="user", content=TEST_MESSAGE)])
            resources = await client.get_resource_usage()
    except OllamaError as error:
        print(f"Ollama smoke test failed [{error.code}]: {error.message}")
        return 1

    print(f"ollama_version={status.version}")
    print(f"model={model.name}")
    print(f"model_size_bytes={model.size_bytes}")
    print(f"first_elapsed_seconds={first.elapsed_seconds:.3f}")
    print(f"second_elapsed_seconds={second.elapsed_seconds:.3f}")
    print(f"first_text={first.text}")
    print(f"second_text={second.text}")
    for usage in resources:
        if usage.model == model.name:
            print(f"loaded_size_bytes={usage.size_bytes}")
            print(f"loaded_size_vram_bytes={usage.size_vram_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
