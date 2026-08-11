"""OpenAI 兼容的最小非流式统一模型客户端。"""

import logging
from time import perf_counter
from typing import Any, Self

import httpx
from pydantic import AnyHttpUrl, SecretStr, ValidationError

from app.core.config import Settings, settings
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
from app.integrations.llm.schemas import ChatMessage, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class LLMClient:
    """通过单一接口调用 OpenAI 兼容的 Chat Completions 服务。"""

    def __init__(self, config: LLMConfig, http_client: httpx.AsyncClient | None = None):
        self.config = config
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=config.timeout_seconds
        )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> "LLMClient":
        provider = app_settings.DEFAULT_MODEL_PROVIDER
        provider_config = {
            "openai": (
                app_settings.OPENAI_MODEL,
                app_settings.OPENAI_BASE_URL,
                app_settings.OPENAI_API_KEY,
            ),
            "openrouter": (
                app_settings.OPENROUTER_MODEL,
                app_settings.OPENROUTER_BASE_URL,
                app_settings.OPENROUTER_API_KEY,
            ),
        }.get(provider)

        if provider_config is None:
            raise LLMConfigurationError(
                f"Provider '{provider}' is not enabled for the cloud LLM smoke test"
            )

        model, api_base, api_key = provider_config
        if not api_key:
            raise LLMConfigurationError(
                f"API key is not configured for provider '{provider}'"
            )
        if not model:
            raise LLMConfigurationError(
                f"Model is not configured for provider '{provider}'"
            )

        try:
            config = LLMConfig(
                provider=provider,
                model=model,
                api_base=AnyHttpUrl(api_base),
                api_key=SecretStr(api_key),
                timeout_seconds=app_settings.LLM_TIMEOUT_SECONDS,
            )
        except ValidationError as error:
            raise LLMConfigurationError("Cloud LLM configuration is invalid") from error

        return cls(config=config, http_client=http_client)

    async def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        if not messages:
            raise LLMConfigurationError("At least one chat message is required")

        started_at = perf_counter()
        logger.info(
            "LLM request started provider=%s model=%s",
            self.config.provider,
            self.config.model,
        )

        try:
            response = await self._http_client.post(
                self.config.chat_completions_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "messages": [message.model_dump() for message in messages],
                    "stream": False,
                },
                timeout=self.config.timeout_seconds,
            )
        except httpx.TimeoutException as error:
            logger.warning("LLM request timed out provider=%s", self.config.provider)
            raise LLMTimeoutError("LLM request timed out") from error
        except httpx.TransportError as error:
            logger.warning("LLM connection failed provider=%s", self.config.provider)
            raise LLMConnectionError(
                "Could not connect to the configured LLM provider"
            ) from error

        self._raise_for_status(response)
        text, response_model = self._parse_response(response)
        elapsed_seconds = perf_counter() - started_at
        logger.info(
            "LLM request completed provider=%s model=%s elapsed_seconds=%.3f",
            self.config.provider,
            response_model,
            elapsed_seconds,
        )
        return LLMResponse(
            text=text,
            provider=self.config.provider,
            model=response_model,
            elapsed_seconds=elapsed_seconds,
        )

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    def _raise_for_status(self, response: httpx.Response) -> None:
        status_code = response.status_code
        if status_code in {401, 403}:
            raise LLMAuthenticationError(
                "LLM provider authentication failed; check the API key",
                status_code=status_code,
            )
        if status_code == 404:
            raise LLMModelNotFoundError(
                "LLM model or endpoint was not found",
                status_code=status_code,
            )
        if status_code == 429:
            raise LLMRateLimitError(
                "LLM provider rate limit exceeded",
                status_code=status_code,
            )
        if status_code >= 400:
            raise LLMProviderError(
                f"LLM provider returned HTTP {status_code}",
                status_code=status_code,
            )

    def _parse_response(self, response: httpx.Response) -> tuple[str, str]:
        try:
            payload: Any = response.json()
            choices = payload["choices"]
            text = choices[0]["message"]["content"]
            response_model = payload.get("model") or self.config.model
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
            raise LLMResponseFormatError(
                "LLM provider returned an incompatible response structure"
            ) from error

        if not isinstance(text, str) or not text.strip():
            raise LLMResponseFormatError("LLM provider returned empty text")
        if not isinstance(response_model, str):
            raise LLMResponseFormatError(
                "LLM provider returned an invalid model identifier"
            )
        return text.strip(), response_model
