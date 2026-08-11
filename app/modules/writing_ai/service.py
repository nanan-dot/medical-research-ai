"""Generation orchestration; external model access is injected for deterministic tests."""

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import cast

from pydantic import AnyHttpUrl, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, TemporarilyUnavailableError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.modules.ai_disclosure.event_normalizer import normalize_event
from app.modules.ai_disclosure.service import AIDisclosureService
from app.modules.model_config.model import ModelConfig
from app.modules.writing_ai.model import WritingAiSuggestion
from app.modules.writing_ai.schema import (
    EvidenceMapping,
    WritingGenerationRequest,
    WritingSuggestionRead,
    WritingTask,
)
from app.modules.writing_project.service import WritingProjectService

GenerationClient = Callable[[WritingGenerationRequest], Awaitable[str]]


class WritingAiService:
    def __init__(
        self, session: AsyncSession, client: GenerationClient | None = None
    ) -> None:
        self._session = session
        self._projects = WritingProjectService(session)
        self._client = client

    async def generate(
        self, project_id: int, request: WritingGenerationRequest
    ) -> WritingSuggestionRead:
        project = await self._projects.get(project_id)
        if project.version != request.expected_version:
            raise ConflictError("Writing project version conflict; reload and retry")
        self._validate_authorized_evidence(project, request)
        config = await self._resolve_config(request.model_config_id)
        try:
            content = await self._generate(request, config)
        except Exception as error:
            raise TemporarilyUnavailableError(
                "Writing model failed; no suggestion was saved"
            ) from error
        mappings = self._mappings(request)
        suggestion = WritingAiSuggestion(
            project_id=project_id,
            task=request.task,
            content=content,
            evidence_mappings_json=json.dumps([item.model_dump() for item in mappings]),
            requires_human_confirmation=True,
        )
        self._session.add(suggestion)
        await self._session.flush()
        await AIDisclosureService(self._session).add_event(
            project_id,
            normalize_event(
                model_name=config.model_name,
                model_version=config.model_name,
                purpose="outline" if request.task == "outline" else "draft",
                input_scope={"papers": len(request.evidence)},
                output_version=f"suggestion:{suggestion.id}",
                human_edited=False,
                is_cloud=config.provider != "ollama",
            ),
        )
        await self._session.refresh(suggestion)
        return self._read(suggestion)

    async def confirm(
        self, project_id: int, suggestion_id: int
    ) -> WritingSuggestionRead:
        suggestion = await self._session.get(WritingAiSuggestion, suggestion_id)
        if suggestion is None or suggestion.project_id != project_id:
            raise ConflictError("Writing suggestion not found for this project")
        suggestion.confirmed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(suggestion)
        return self._read(suggestion)

    async def _resolve_config(self, config_id: int | None) -> ModelConfig:
        config = await self._session.get(ModelConfig, config_id) if config_id else None
        if config is None:
            raise ConflictError("An explicit model configuration is required")
        if config.provider != "ollama" and not config.allow_cloud_content:
            raise ConflictError(
                "Cloud content processing is not authorized for this model"
            )
        return config

    async def _generate(
        self, request: WritingGenerationRequest, config: ModelConfig
    ) -> str:
        if self._client is not None:
            return await self._client(request)
        api_key = (
            "ollama"
            if config.provider == "ollama"
            else SecretCipher().decrypt(config.encrypted_api_key or "")
        )
        messages = [
            ChatMessage(
                role="system",
                content="Produce a writing suggestion only from supplied evidence. Mark unsupported claims as [needs verification].",
            ),
            ChatMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": request.task,
                        "evidence": [item.model_dump() for item in request.evidence],
                    },
                    ensure_ascii=False,
                ),
            ),
        ]
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model_name,
            api_base=AnyHttpUrl(config.api_base),
            api_key=SecretStr(api_key),
        )
        async with LLMClient(llm_config) as client:
            return (await client.chat(messages)).text

    async def generate_text(self, prompt: str, config: ModelConfig) -> str:
        """Execute a configured model request for sibling writing workflows."""
        api_key = (
            "ollama"
            if config.provider == "ollama"
            else SecretCipher().decrypt(config.encrypted_api_key or "")
        )
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model_name,
            api_base=AnyHttpUrl(config.api_base),
            api_key=SecretStr(api_key),
        )
        async with LLMClient(llm_config) as client:
            return (await client.chat([ChatMessage(role="user", content=prompt)])).text

    @staticmethod
    def _validate_authorized_evidence(
        project, request: WritingGenerationRequest
    ) -> None:
        allowed = {item.id for item in project.evidence_references}
        if not all(item.reference_id in allowed for item in request.evidence):
            raise ConflictError(
                "Each requested evidence item must be explicitly linked to the project"
            )

    @staticmethod
    def _mappings(request: WritingGenerationRequest) -> list[EvidenceMapping]:
        return [
            EvidenceMapping(
                evidence_ref=item.reference_id,
                citation_id=f"writing-evidence:{item.reference_id}",
            )
            for item in request.evidence
        ]

    @staticmethod
    def _read(entity: WritingAiSuggestion) -> WritingSuggestionRead:
        return WritingSuggestionRead(
            id=entity.id,
            project_id=entity.project_id,
            task=cast(WritingTask, entity.task),
            content=entity.content,
            evidence_mappings=[
                EvidenceMapping.model_validate(item)
                for item in json.loads(entity.evidence_mappings_json)
            ],
            requires_human_confirmation=entity.requires_human_confirmation,
            confirmed_at=entity.confirmed_at,
            adopted_version=entity.adopted_version,
            created_at=entity.created_at,
        )
