"""Topic parsing, safe model routing, editing, and immutable version creation."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import AnyHttpUrl, SecretStr, ValidationError

from app.common.exceptions import AIModelError, ConflictError, NotFoundError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.integrations.ollama.client import OllamaClient
from app.modules.model_config.model import ModelConfig
from app.modules.model_config.repository import ModelConfigRepository
from app.modules.topic_structuring.model import TopicStructuring, TopicStructuringVersion
from app.modules.topic_structuring.prompts import build_topic_structuring_prompt
from app.modules.topic_structuring.repository import TopicStructuringRepository
from app.modules.topic_structuring.schema import (
    EditableField,
    TopicStructureCandidate,
    TopicStructuringParseRequest,
    TopicStructuringPatchRequest,
    TopicStructuringRead,
    TopicStructuringVersionRead,
)
from app.modules.topic_structuring.structure_classifier import classify_structuring_status

CandidateExtractor = Callable[[str, int | None], Awaitable[str]]


class TopicStructuringService:
    """Persist user-editable candidates without changing their original topic."""

    def __init__(self, session: AsyncSession, *, candidate_extractor: CandidateExtractor | None = None):
        self._repository = TopicStructuringRepository(session)
        self._model_configs = ModelConfigRepository(session)
        self._candidate_extractor = candidate_extractor or self._extract_with_routed_model

    async def parse(self, payload: TopicStructuringParseRequest) -> TopicStructuringRead:
        normalized_topic = " ".join(payload.topic.split())
        raw_candidate = await self._candidate_extractor(
            build_topic_structuring_prompt(normalized_topic), payload.model_config_id
        )
        try:
            candidate = self._normalize_candidate(TopicStructureCandidate.model_validate_json(raw_candidate))
        except (ValidationError, ValueError) as error:
            raise AIModelError("The configured model returned an invalid topic structure") from error
        entity = await self._repository.create(TopicStructuring(original_topic=payload.topic, current_version=1))
        version = await self._repository.create_version(self._new_version(entity.id, 1, candidate))
        return self._to_read(entity, version, [version])

    async def get(self, structuring_id: int) -> TopicStructuringRead:
        entity = await self._get_entity(structuring_id)
        version = await self._get_version(entity.id, entity.current_version)
        return self._to_read(entity, version, await self._repository.list_versions(entity.id))

    async def patch(
        self, structuring_id: int, payload: TopicStructuringPatchRequest
    ) -> TopicStructuringRead:
        entity = await self._get_entity(structuring_id)
        current = await self._get_version(entity.id, entity.current_version)
        candidate = TopicStructureCandidate.model_validate_json(current.structured_json)
        if payload.field is not None:
            self._apply_field_update(candidate, payload.field, payload.value)
        else:
            self._apply_clarification_answer(candidate, payload.clarification_question_id, payload.answer)
        candidate = self._normalize_candidate(candidate)
        next_version = entity.current_version + 1
        version = await self._repository.create_version(self._new_version(entity.id, next_version, candidate))
        entity.current_version = next_version
        entity.updated_at = datetime.now(UTC)
        entity = await self._repository.save(entity)
        return self._to_read(entity, version, await self._repository.list_versions(entity.id))

    async def _get_entity(self, structuring_id: int) -> TopicStructuring:
        entity = await self._repository.get(structuring_id)
        if entity is None:
            raise NotFoundError(f"Topic structuring not found: {structuring_id}")
        return entity

    async def _get_version(self, structuring_id: int, version: int) -> TopicStructuringVersion:
        entity = await self._repository.get_version(structuring_id, version)
        if entity is None:
            raise NotFoundError(f"Topic structuring version not found: {structuring_id}/{version}")
        return entity

    async def _extract_with_routed_model(self, prompt: str, model_config_id: int | None) -> str:
        config = await self._resolve_model_config(model_config_id)
        message = [ChatMessage(role="user", content=prompt)]
        if config.provider == "ollama":
            async with OllamaClient(base_url=config.api_base, model=config.model_name) as client:
                return (await client.chat(message)).text
        api_key = SecretCipher().decrypt(config.encrypted_api_key or "")
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model_name,
            api_base=AnyHttpUrl(config.api_base),
            api_key=SecretStr(api_key),
            timeout_seconds=60,
        )
        async with LLMClient(llm_config) as client:
            return (await client.chat(message)).text

    async def _resolve_model_config(self, model_config_id: int | None) -> ModelConfig:
        if model_config_id is not None:
            config = await self._model_configs.get(model_config_id)
            if config is None:
                raise NotFoundError(f"Model config not found: {model_config_id}")
            if config.provider != "ollama" and not config.allow_cloud_content:
                raise ConflictError("Cloud topic parsing requires explicit content-transfer authorization")
            return config
        cloud_configs = [
            config
            for config in await self._model_configs.list()
            if config.provider != "ollama" and config.allow_cloud_content
        ]
        default_config = next((config for config in cloud_configs if config.is_default), None)
        if default_config is not None:
            return default_config
        if cloud_configs:
            return cloud_configs[0]
        raise ConflictError(
            "No model is configured for public topic parsing; configure a cloud API key or select Ollama explicitly"
        )

    @staticmethod
    def _normalize_candidate(candidate: TopicStructureCandidate) -> TopicStructureCandidate:
        status = classify_structuring_status(
            candidate.structuring_status,
            disease=candidate.disease,
            target=candidate.target,
            intervention=candidate.intervention,
            mechanism=candidate.mechanism,
            comparator=candidate.comparator,
            outcome=candidate.outcome,
        )
        candidate.structuring_status = status
        if status == "unstructured":
            candidate.reason = candidate.reason or "The topic lacks enough explicit information for a reliable PICO/PECO or mechanism template."
        return candidate

    @staticmethod
    def _apply_field_update(
        candidate: TopicStructureCandidate, field: EditableField, value: str | list[str] | None
    ) -> None:
        if field == "focus_points":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ConflictError("focus_points must be a list of text values")
            candidate.focus_points = value
        else:
            if not isinstance(value, str):
                raise ConflictError(f"{field} must be text")
            setattr(candidate, field, value)
        candidate.known_fields[field] = True

    @staticmethod
    def _apply_clarification_answer(
        candidate: TopicStructureCandidate, question_id: object, answer: str | None
    ) -> None:
        if answer is None:
            raise ConflictError("Clarification answer is required")
        question = next((item for item in candidate.clarification_questions if item.id == question_id), None)
        if question is None:
            raise NotFoundError("Clarification question not found")
        question.answered = True
        if question.clarifies_field == "general":
            return
        field = cast(EditableField, question.clarifies_field)
        setattr(candidate, field, answer)
        candidate.known_fields[field] = True

    @staticmethod
    def _new_version(
        structuring_id: int, version: int, candidate: TopicStructureCandidate
    ) -> TopicStructuringVersion:
        return TopicStructuringVersion(
            topic_structuring_id=structuring_id,
            version=version,
            structured_json=candidate.model_dump_json(),
        )

    @staticmethod
    def _to_read(
        entity: TopicStructuring,
        current_version: TopicStructuringVersion,
        versions: list[TopicStructuringVersion],
    ) -> TopicStructuringRead:
        return TopicStructuringRead(
            id=entity.id,
            original_topic=entity.original_topic,
            current_version=entity.current_version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            candidate=TopicStructureCandidate.model_validate_json(current_version.structured_json),
            versions=[
                TopicStructuringVersionRead(
                    version=item.version,
                    created_at=item.created_at,
                    candidate=TopicStructureCandidate.model_validate_json(item.structured_json),
                )
                for item in versions
            ],
        )
