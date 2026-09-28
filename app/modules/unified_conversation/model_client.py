"""复用用户已保存的模型与云端授权；本地配置通过现有 Ollama 适配器。"""

from typing import Protocol

from pydantic import AnyHttpUrl, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import LLMConfigurationError
from app.integrations.llm.schemas import ChatMessage, LLMConfig, LLMResponse
from app.integrations.ollama.client import OllamaClient
from app.integrations.paperqa2 import PaperQA2Client, create_paperqa2_client
from app.modules.model_config.model import ModelConfig


class ChatClient(Protocol):
    async def chat(self, messages: list[ChatMessage]) -> LLMResponse: ...
    async def aclose(self) -> None: ...


async def selected_model(session: AsyncSession) -> ModelConfig | None:
    return await session.scalar(
        select(ModelConfig).where(ModelConfig.is_default.is_(True))
    )


def require_cloud_permission(model: ModelConfig | None) -> None:
    if model is None or not model.allow_cloud_content:
        raise LLMConfigurationError("请在模型设置中明确授权云端内容传输")


async def chat_client(session: AsyncSession) -> ChatClient:
    model = await selected_model(session)
    if model is None:
        if settings.DEFAULT_MODEL_PROVIDER == "ollama":
            return OllamaClient.from_settings()
        raise LLMConfigurationError("请配置默认模型并授权云端内容传输")
    if model.provider == "ollama":
        return OllamaClient(
            base_url=model.api_base.rstrip("/").removesuffix("/v1"),
            model=model.model_name,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        )
    require_cloud_permission(model)
    key = (
        SecretCipher().decrypt(model.encrypted_api_key)
        if model.encrypted_api_key
        else ""
    )
    if not key:
        raise LLMConfigurationError("默认模型缺少凭证")
    return LLMClient(
        LLMConfig(
            provider=model.provider,
            model=model.model_name,
            api_base=AnyHttpUrl(model.api_base),
            api_key=SecretStr(key),
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
    )


async def paper_client(session: AsyncSession) -> PaperQA2Client:
    model = await selected_model(session)
    if model is None:
        if settings.DEFAULT_MODEL_PROVIDER != "ollama":
            require_cloud_permission(model)
        return create_paperqa2_client()
    if model.provider != "ollama":
        require_cloud_permission(model)
    prefix = model.provider.upper()
    overrides = {
        "DEFAULT_MODEL_PROVIDER": model.provider,
        f"{prefix}_MODEL": model.model_name,
        f"{prefix}_BASE_URL": model.api_base.rstrip("/").removesuffix("/v1")
        if model.provider == "ollama"
        else model.api_base,
    }
    if model.provider != "ollama":
        overrides[f"{prefix}_API_KEY"] = (
            SecretCipher().decrypt(model.encrypted_api_key)
            if model.encrypted_api_key
            else ""
        )
    return create_paperqa2_client(settings.model_copy(update=overrides))
