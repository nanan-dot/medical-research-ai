from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urlparse
from pydantic import AnyHttpUrl, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.exceptions import ConflictError, NotFoundError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import LLMClientError
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.integrations.ollama.client import OllamaClient
from app.modules.model_config.model import ModelConfig
from app.modules.model_config.repository import ModelConfigRepository
from app.modules.model_config.schema import (
    ConnectionTestResult,
    ModelConfigCreate,
    ModelConfigRead,
    Provider,
)

Tester = Callable[[ModelConfig, str | None], Awaitable[None]]


class ModelConfigService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        cipher: SecretCipher | None = None,
        tester: Tester | None = None,
    ):
        self.repo = ModelConfigRepository(session)
        self.cipher = cipher
        self.tester = tester or self._test_connection

    async def create(self, data: ModelConfigCreate):
        self._validate_base(data)
        cipher = self.cipher or SecretCipher()
        if data.is_default:
            await self.repo.clear_defaults()
        now = datetime.now(UTC)
        entity = await self.repo.create(
            ModelConfig(
                deployment_mode=data.deployment_mode.value,
                provider=data.provider.value,
                api_base=data.api_base.rstrip("/"),
                encrypted_api_key=cipher.encrypt(data.api_key)
                if data.api_key
                else None,
                model_name=data.model_name,
                is_default=data.is_default,
                allow_cloud_content=data.allow_cloud_content,
                created_at=now,
                updated_at=now,
            )
        )
        return self._read(entity)

    async def list(self):
        return [self._read(item) for item in await self.repo.list()]

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Model config not found: {id}")
        return entity

    async def delete(self, id: int):
        await self.repo.delete(await self.get(id))

    async def test(self, id: int, acknowledge_cost: bool):
        entity = await self.get(id)
        if entity.provider != "ollama" and not acknowledge_cost:
            raise ConflictError(
                "Connection test may incur cloud cost; explicit acknowledgement is required"
            )
        key = (
            (self.cipher or SecretCipher()).decrypt(entity.encrypted_api_key)
            if entity.encrypted_api_key
            else None
        )
        try:
            await self.tester(entity, key)
        except (LLMClientError, ValueError) as exc:
            raise ConflictError("Model connection test failed") from exc
        return ConnectionTestResult(success=True, message="Connection succeeded")

    @staticmethod
    def _validate_base(data):
        parsed = urlparse(data.api_base)
        if data.provider == Provider.OLLAMA:
            OllamaClient(base_url=data.api_base, model=data.model_name)
        elif parsed.scheme != "https" or not parsed.hostname:
            raise ConflictError("Cloud API Base must use HTTPS")

    @staticmethod
    async def _test_connection(entity, key):
        if entity.provider == "ollama":
            async with OllamaClient(
                base_url=entity.api_base, model=entity.model_name
            ) as client:
                await client.ensure_model_available()
        else:
            config = LLMConfig(
                provider=entity.provider,
                model=entity.model_name,
                api_base=AnyHttpUrl(entity.api_base),
                api_key=SecretStr(key or ""),
                timeout_seconds=30,
            )
            async with LLMClient(config) as client:
                await client.chat([ChatMessage(role="user", content="Reply OK")])

    @staticmethod
    def _read(entity):
        return ModelConfigRead(
            id=entity.id,
            deployment_mode=entity.deployment_mode,
            provider=entity.provider,
            api_base=entity.api_base,
            model_name=entity.model_name,
            is_default=entity.is_default,
            allow_cloud_content=entity.allow_cloud_content,
            api_key_masked="••••••••" if entity.encrypted_api_key else None,
        )
