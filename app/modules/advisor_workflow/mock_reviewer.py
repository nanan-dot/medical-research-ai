"""本地优先的模拟导师模型调用与结构化结果校验。"""

import json
from typing import Literal

from pydantic import AnyHttpUrl, SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, TemporarilyUnavailableError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import LLMClientError
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.modules.advisor_workflow.schema import AdvisorNoteCreate
from app.modules.model_config.model import ModelConfig
from app.modules.research_direction.model import ResearchDirection

Provider = Literal["ollama", "openai", "openrouter"]
MOCK_WARNING = "AI simulated review; it is not a real advisor judgment."
SYSTEM_PROMPT = """You are a strict research-methods reviewer. Return JSON only with keys:
decision (accept|revise|reject), summary, points, literature_gaps, experiment_conditions.
Each point must contain field_name, topic, content, severity (blocker|major|minor).
Do not invent papers, identifiers, statistics, clinical facts, or evidence. Focus on gaps,
scope, feasibility, ethics, and missing validation. This is an AI simulation, not advisor advice."""


class MockReviewGenerator:
    """按显式配置路由模型；隐私数据默认只允许本地 Ollama。"""

    def __init__(self, session: AsyncSession, cipher: SecretCipher | None = None) -> None:
        self._session = session
        self._cipher = cipher

    async def generate(
        self,
        direction: ResearchDirection,
        *,
        provider: Provider | None = None,
        model_config_id: int | None = None,
    ) -> AdvisorNoteCreate:
        config = await self._resolve_config(provider, model_config_id)
        api_key = self._api_key(config)
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model_name,
            api_base=AnyHttpUrl(config.api_base),
            api_key=SecretStr(api_key),
        )
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=self._direction_context(direction)),
        ]
        try:
            async with LLMClient(llm_config) as client:
                response = await client.chat(messages)
        except LLMClientError as error:
            raise TemporarilyUnavailableError(
                "Configured mock-review model is unavailable; no cloud fallback was attempted"
            ) from error
        return self._parse(response.text)

    async def _resolve_config(
        self, provider: Provider | None, model_config_id: int | None
    ) -> ModelConfig:
        if model_config_id is not None:
            config = await self._session.get(ModelConfig, model_config_id)
        else:
            statement = select(ModelConfig).where(ModelConfig.is_default.is_(True))
            config = (await self._session.execute(statement)).scalar_one_or_none()
        if config is None:
            raise ConflictError(
                "Mock review model is not configured; configure local Ollama or explicitly select a cloud model"
            )
        if provider is not None and config.provider != provider:
            raise ConflictError("Selected model configuration does not match the requested provider")
        explicit_cloud = model_config_id is not None and provider is not None
        if config.provider != "ollama" and not (explicit_cloud and config.allow_cloud_content):
            raise ConflictError(
                "Private research content requires local Ollama unless an allowed cloud model is explicitly selected"
            )
        return config

    def _api_key(self, config: ModelConfig) -> str:
        if config.provider == "ollama":
            return "ollama"
        if not config.encrypted_api_key:
            raise ConflictError("Selected cloud model has no API key")
        cipher = self._cipher or SecretCipher()
        return cipher.decrypt(config.encrypted_api_key)

    @staticmethod
    def _direction_context(direction: ResearchDirection) -> str:
        fields = {
            "name": direction.name,
            "question": direction.question,
            "gap": direction.gap,
            "current_evidence": direction.current_evidence,
            "ethics_risk": direction.ethics_risk,
            "resource_risk": direction.resource_risk,
        }
        return json.dumps(fields, ensure_ascii=False)

    @staticmethod
    def _parse(text: str) -> AdvisorNoteCreate:
        normalized = text.strip()
        if normalized.startswith("```"):
            normalized = normalized.removeprefix("```json").removeprefix("```")
            normalized = normalized.removesuffix("```").strip()
        try:
            payload = AdvisorNoteCreate.model_validate_json(normalized)
        except (ValidationError, ValueError) as error:
            raise TemporarilyUnavailableError(
                "Mock-review model returned invalid structured output"
            ) from error
        payload.summary = f"{MOCK_WARNING} {payload.summary}"
        return payload
