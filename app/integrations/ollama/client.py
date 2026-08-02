"""通过统一 ``LLMClient.chat`` 调用本机 Ollama。"""

import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import AnyHttpUrl, SecretStr, ValidationError

from app.core.config import Settings, settings
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMResponseFormatError,
    LLMTimeoutError,
)
from app.integrations.llm.schemas import ChatMessage, LLMConfig, LLMResponse
from app.integrations.ollama.exceptions import (
    OllamaConfigurationError,
    OllamaIncompatibleServiceError,
    OllamaModelNotFoundError,
    OllamaResourceError,
    OllamaResponseError,
    OllamaServiceUnavailableError,
    OllamaTimeoutError,
)
from app.integrations.ollama.schemas import OllamaModelInfo, OllamaResourceUsage, OllamaStatus


class OllamaClient:
    """只允许回环地址且不会配置任何云端回退的本地模型客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._validate_local_base_url()
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout_seconds,
            trust_env=False,
        )

        try:
            llm_config = LLMConfig(
                provider="ollama",
                model=model,
                api_base=AnyHttpUrl(f"{self.base_url}/v1"),
                api_key=SecretStr("ollama"),
                timeout_seconds=timeout_seconds,
            )
        except ValidationError as error:
            raise OllamaConfigurationError("Ollama configuration is invalid") from error
        self._llm_client = LLMClient(config=llm_config, http_client=self._http_client)

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> "OllamaClient":
        if not app_settings.OLLAMA_MODEL:
            raise OllamaConfigurationError("OLLAMA_MODEL is not configured")
        return cls(
            base_url=app_settings.OLLAMA_BASE_URL,
            model=app_settings.OLLAMA_MODEL,
            timeout_seconds=app_settings.OLLAMA_TIMEOUT_SECONDS,
            http_client=http_client,
        )

    async def check_service(self) -> OllamaStatus:
        payload = await self._get_json("/api/version")
        version = payload.get("version")
        if not isinstance(version, str) or not version:
            raise OllamaIncompatibleServiceError(
                "The configured port did not return an Ollama version response"
            )
        return OllamaStatus(version=version)

    async def list_models(self) -> list[OllamaModelInfo]:
        payload = await self._get_json("/api/tags")
        raw_models = payload.get("models")
        if not isinstance(raw_models, list):
            raise OllamaIncompatibleServiceError("Ollama returned an invalid model list")

        models: list[OllamaModelInfo] = []
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            name = raw_model.get("name") or raw_model.get("model")
            size = raw_model.get("size", 0)
            if isinstance(name, str) and isinstance(size, int):
                models.append(OllamaModelInfo(name=name, size_bytes=size))
        return models

    async def ensure_model_available(self) -> OllamaModelInfo:
        models = await self.list_models()
        for model in models:
            if model.name == self.model:
                return model
        raise OllamaModelNotFoundError(
            f"Ollama model '{self.model}' is not installed; run 'ollama pull {self.model}'"
        )

    async def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        try:
            return await self._llm_client.chat(messages)
        except LLMConnectionError as error:
            raise OllamaServiceUnavailableError(
                "Ollama is not reachable; start the local Ollama service"
            ) from error
        except LLMModelNotFoundError as error:
            raise OllamaModelNotFoundError(
                f"Ollama model '{self.model}' is not installed"
            ) from error
        except LLMTimeoutError as error:
            raise OllamaTimeoutError(
                "Ollama request timed out; first load may need a larger timeout"
            ) from error
        except LLMResponseFormatError as error:
            raise OllamaResponseError("Ollama returned empty or incompatible text") from error
        except LLMProviderError as error:
            if error.status_code and error.status_code >= 500:
                raise OllamaResourceError(
                    "Ollama failed to run the model; check RAM, VRAM, and Ollama logs"
                ) from error
            raise OllamaResponseError("Ollama returned a request error") from error

    async def get_resource_usage(self) -> list[OllamaResourceUsage]:
        payload = await self._get_json("/api/ps")
        raw_models = payload.get("models")
        if not isinstance(raw_models, list):
            raise OllamaIncompatibleServiceError("Ollama returned invalid resource data")

        usage: list[OllamaResourceUsage] = []
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            model = raw_model.get("name") or raw_model.get("model")
            size = raw_model.get("size", 0)
            size_vram = raw_model.get("size_vram", 0)
            if isinstance(model, str) and isinstance(size, int) and isinstance(size_vram, int):
                usage.append(
                    OllamaResourceUsage(
                        model=model,
                        size_bytes=size,
                        size_vram_bytes=size_vram,
                    )
                )
        return usage

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            response = await self._http_client.get(
                f"{self.base_url}{path}", timeout=self.timeout_seconds
            )
        except httpx.TimeoutException as error:
            raise OllamaTimeoutError("Ollama service check timed out") from error
        except httpx.TransportError as error:
            raise OllamaServiceUnavailableError(
                "Ollama is not reachable; start the local Ollama service"
            ) from error

        if response.status_code >= 400:
            raise OllamaServiceUnavailableError(
                f"Ollama service returned HTTP {response.status_code}",
                status_code=response.status_code,
            )
        try:
            payload: Any = response.json()
        except ValueError as error:
            raise OllamaIncompatibleServiceError(
                "The configured port did not return an Ollama JSON response"
            ) from error
        if not isinstance(payload, dict):
            raise OllamaIncompatibleServiceError("Ollama returned an incompatible response")
        return payload

    def _validate_local_base_url(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise OllamaConfigurationError("OLLAMA_BASE_URL must be a local HTTP URL")
        try:
            is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            is_loopback = parsed.hostname == "localhost"
        if not is_loopback:
            raise OllamaConfigurationError(
                "OLLAMA_BASE_URL must use localhost or a loopback address"
            )
