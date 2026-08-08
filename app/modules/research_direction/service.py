"""候选研究方向的生成、详情懒加载与编辑服务。"""

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Literal, cast

from pydantic import AnyHttpUrl, SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AIModelError, ConflictError, NotFoundError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.integrations.ollama.client import OllamaClient
from app.modules.comparison.shared import SourceRef
from app.modules.evidence_analysis.repository import EvidenceAnalysisRepository
from app.modules.model_config.model import ModelConfig
from app.modules.model_config.repository import ModelConfigRepository
from app.modules.research_conditions.repository import ResearchConditionsRepository
from app.modules.research_direction.generator import parse_candidates
from app.modules.research_direction.model import ResearchDirection
from app.modules.research_direction.prompts import build_candidates_prompt, build_details_prompt
from app.modules.research_direction.repository import ResearchDirectionRepository
from app.modules.research_direction.schema import (
    CandidateCore, DirectionDetails, EvidenceStatement, GenerationMetadata, GenerationStrategy,
    GroundedText, Priority, ResearchDirectionGenerateRequest, ResearchDirectionPatch,
    ResearchDirectionRead,
)

ModelGenerator = Callable[[str, int | None, bool], Awaitable[str]]


class ResearchDirectionService:
    """将私有研究条件与公开矩阵在明确模型路由下组合为候选方向。"""

    def __init__(self, session: AsyncSession, *, model_generator: ModelGenerator | None = None) -> None:
        self._repository = ResearchDirectionRepository(session)
        self._conditions = ResearchConditionsRepository(session)
        self._evidence = EvidenceAnalysisRepository(session)
        self._model_configs = ModelConfigRepository(session)
        self._model_generator = model_generator or self._generate_with_routed_model

    async def generate(self, request: ResearchDirectionGenerateRequest) -> list[ResearchDirectionRead]:
        conditions_entity = await self._conditions.get(request.research_conditions_id)
        if conditions_entity is None:
            raise NotFoundError(f"Research conditions not found: {request.research_conditions_id}")
        condition_version = await self._conditions.get_version(
            conditions_entity.id, conditions_entity.current_version
        )
        if condition_version is None:
            raise NotFoundError("Current research conditions version not found")
        matrix = await self._evidence.get_matrix(request.evidence_matrix_id)
        if matrix is None:
            raise NotFoundError(f"Evidence matrix not found: {request.evidence_matrix_id}")
        context, allowed_sources = await self._load_evidence_context(matrix.id)
        if not allowed_sources:
            raise ConflictError("Evidence matrix has no PMID/DOI sources; cannot generate grounded directions")
        prompt = build_candidates_prompt(json.loads(condition_version.conditions_json), context, request.candidate_count)
        raw_response = await self._model_generator(prompt, request.model_config_id, True)
        try:
            candidates = parse_candidates(raw_response, allowed_sources)
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise AIModelError("The configured model returned invalid or ungrounded candidate directions") from error
        if len(candidates) < request.candidate_count:
            raise AIModelError("Model returned fewer non-duplicate candidate directions than requested")
        if _can_generate_cross_topic(context) and not any(
            item.generation_strategy == "cross-topic" for item in candidates
        ):
            raise AIModelError("Model did not provide the required cross-topic candidate")
        created_at = datetime.now(UTC)
        entities = [
            self._new_entity(candidate, request, conditions_entity.current_version, matrix.version, created_at)
            for candidate in candidates[:request.candidate_count]
        ]
        return [self._to_read(entity) for entity in await self._repository.create_many(entities)]

    async def get(self, direction_id: int) -> ResearchDirectionRead:
        return self._to_read(await self._get_entity(direction_id))

    async def get_details(self, direction_id: int) -> ResearchDirectionRead:
        """只读取已缓存详情，绝不在 GET 请求中触发模型调用。"""
        return await self.get(direction_id)

    async def generate_details(self, direction_id: int, model_config_id: int | None) -> ResearchDirectionRead:
        entity = await self._get_entity(direction_id)
        if entity.methods is not None:
            return self._to_read(entity)
        context, _ = await self._load_evidence_context(entity.evidence_matrix_id)
        raw_response = await self._model_generator(
            build_details_prompt(self._to_read(entity).model_dump(mode="json"), context), model_config_id, True
        )
        try:
            details = DirectionDetails.model_validate_json(raw_response)
        except (ValidationError, ValueError) as error:
            raise AIModelError("The configured model returned invalid direction details") from error
        for field, value in details.model_dump().items():
            setattr(entity, field, value)
        entity.updated_at = datetime.now(UTC)
        entity = await self._repository.save(entity)
        return self._to_read(entity)

    async def patch(self, direction_id: int, payload: ResearchDirectionPatch) -> ResearchDirectionRead:
        entity = await self._get_entity(direction_id)
        updates = payload.model_dump(exclude_none=True)
        merge_source_ids = updates.pop("merge_source_ids", None)
        for field, value in updates.items():
            if field == "controversy":
                entity.controversy = value.text
                entity.controversy_sources_json = json.dumps(
                    [source.model_dump(exclude_none=True) for source in value.sources], ensure_ascii=False
                )
                continue
            setattr(entity, field, value)
        if merge_source_ids is not None:
            if direction_id in merge_source_ids:
                raise ConflictError("A direction cannot merge itself")
            sources = await self._repository.list_by_ids(merge_source_ids)
            if len(sources) != len(set(merge_source_ids)):
                raise NotFoundError("One or more merge source directions were not found")
            if any(source.evidence_matrix_id != entity.evidence_matrix_id for source in sources):
                raise ConflictError("Only directions from the same evidence matrix can be merged")
            if any(source.status != "active" for source in sources):
                raise ConflictError("Only active directions can be merged")
            merged_ids = set(json.loads(entity.merged_from_ids_json))
            merged_ids.update(merge_source_ids)
            entity.merged_from_ids_json = json.dumps(sorted(merged_ids))
            for source in sources:
                source.status = "merged"
                source.merged_into_id = entity.id
                source.version += 1
                source.updated_at = datetime.now(UTC)
        entity.version += 1
        entity.updated_at = datetime.now(UTC)
        return self._to_read(await self._repository.save(entity))

    async def delete(self, direction_id: int) -> None:
        await self._repository.delete(await self._get_entity(direction_id))

    async def _load_evidence_context(self, matrix_id: int) -> tuple[list[dict[str, object]], set[tuple[str | None, str | None, str]]]:
        documents = await self._evidence.list_documents(matrix_id)
        cells = await self._evidence.list_cells(matrix_id)
        document_cells: dict[int, list[dict[str, object]]] = {}
        allowed_sources: set[tuple[str | None, str | None, str]] = set()
        for cell in cells:
            try:
                sources = [SourceRef.model_validate(item) for item in json.loads(cell.sources)]
            except (json.JSONDecodeError, ValidationError):
                sources = []
            for source in sources:
                allowed_sources.add((source.pmid, source.doi, source.locator))
            document_cells.setdefault(cell.document_id, []).append({
                "field_key": cell.field_key, "value": cell.cell_value,
                "sources": [source.model_dump(exclude_none=True) for source in sources],
            })
        return ([{"document_id": item.document_id, "cells": document_cells.get(item.document_id, [])} for item in documents], allowed_sources)

    async def _get_entity(self, direction_id: int) -> ResearchDirection:
        entity = await self._repository.get(direction_id)
        if entity is None:
            raise NotFoundError(f"Research direction not found: {direction_id}")
        return entity

    async def _generate_with_routed_model(self, prompt: str, model_config_id: int | None, has_private_data: bool) -> str:
        config = await self._resolve_model_config(model_config_id, has_private_data)
        messages = [ChatMessage(role="user", content=prompt)]
        if config.provider == "ollama":
            async with OllamaClient(base_url=config.api_base, model=config.model_name) as client:
                return (await client.chat(messages)).text
        api_key = SecretCipher().decrypt(config.encrypted_api_key or "")
        llm_config = LLMConfig(provider=config.provider, model=config.model_name, api_base=AnyHttpUrl(config.api_base), api_key=SecretStr(api_key), timeout_seconds=60)
        async with LLMClient(llm_config) as client:
            return (await client.chat(messages)).text

    async def _resolve_model_config(self, model_config_id: int | None, has_private_data: bool) -> ModelConfig:
        if model_config_id is not None:
            config = await self._model_configs.get(model_config_id)
            if config is None:
                raise NotFoundError(f"Model config not found: {model_config_id}")
            if config.provider != "ollama" and not config.allow_cloud_content:
                raise ConflictError("Cloud direction generation requires explicit content-transfer authorization")
            return config
        if has_private_data:
            local_configs = [item for item in await self._model_configs.list() if item.provider == "ollama"]
            default_config = next((item for item in local_configs if item.is_default), None)
            if default_config is not None:
                return default_config
            if local_configs:
                return local_configs[0]
            raise ConflictError("No local model is configured for private conditions; install Ollama or explicitly select a cloud model")
        raise ConflictError("No model configuration was selected")

    @staticmethod
    def _new_entity(
        candidate: CandidateCore,
        request: ResearchDirectionGenerateRequest,
        conditions_version: int,
        matrix_version: int,
        generated_at: datetime,
    ) -> ResearchDirection:
        metadata = GenerationMetadata(
            model_version="configured-model",
            input_conditions_version=conditions_version,
            evidence_matrix_version=matrix_version,
            strategy=candidate.generation_strategy,
            generated_at=generated_at,
        )
        return ResearchDirection(
            research_conditions_id=request.research_conditions_id,
            evidence_matrix_id=request.evidence_matrix_id,
            name=candidate.name,
            question=candidate.question,
            research_object=candidate.research_object,
            study_type=candidate.study_type,
            evidence_json=json.dumps(
                [item.model_dump(mode="json", exclude_none=True) for item in candidate.evidence],
                ensure_ascii=False,
            ),
            current_evidence=candidate.current_evidence.text,
            current_evidence_sources_json=json.dumps(
                [source.model_dump(exclude_none=True) for source in candidate.current_evidence.sources],
                ensure_ascii=False,
            ),
            controversy=candidate.controversy.text,
            controversy_sources_json=json.dumps(
                [source.model_dump(exclude_none=True) for source in candidate.controversy.sources],
                ensure_ascii=False,
            ),
            gap=candidate.gap,
            novelty_uncertainty=candidate.novelty_uncertainty,
            priority=candidate.priority,
            generation_strategy=candidate.generation_strategy,
            generation_metadata_json=metadata.model_dump_json(),
            version=1,
        )

    @staticmethod
    def _to_read(entity: ResearchDirection) -> ResearchDirectionRead:
        return ResearchDirectionRead(
            id=entity.id,
            research_conditions_id=entity.research_conditions_id,
            evidence_matrix_id=entity.evidence_matrix_id,
            name=entity.name,
            question=entity.question,
            research_object=entity.research_object,
            study_type=entity.study_type,
            evidence=[EvidenceStatement.model_validate(item) for item in json.loads(entity.evidence_json)],
            current_evidence=GroundedText(
                text=entity.current_evidence,
                sources=[SourceRef.model_validate(item) for item in json.loads(entity.current_evidence_sources_json)],
            ),
            controversy=GroundedText(
                text=entity.controversy,
                sources=[SourceRef.model_validate(item) for item in json.loads(entity.controversy_sources_json)],
            ),
            gap=entity.gap,
            novelty_uncertainty=entity.novelty_uncertainty,
            priority=cast(Priority, entity.priority),
            generation_strategy=cast(GenerationStrategy, entity.generation_strategy),
            metadata=GenerationMetadata.model_validate_json(entity.generation_metadata_json),
            methods=entity.methods,
            requirements=entity.requirements,
            difficulty=entity.difficulty,
            time_risk=entity.time_risk,
            resource_risk=entity.resource_risk,
            ethics_risk=entity.ethics_risk,
            search_terms=entity.search_terms,
            advisor_questions=entity.advisor_questions,
            merged_from_ids=json.loads(entity.merged_from_ids_json),
            status=cast(Literal["active", "merged"], entity.status),
            merged_into_id=entity.merged_into_id,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


def _can_generate_cross_topic(context: list[dict[str, object]]) -> bool:
    """两个以上有证据的文献单元才要求跨主题，避免空矩阵强行碰撞。"""
    documented_topics = {
        cell["value"]
        for document in context
        for cell in _context_cells(document)
        if isinstance(cell, dict) and cell.get("sources") and cell.get("value") not in {"", "缺失"}
    }
    return len(documented_topics) >= 2


def _context_cells(document: dict[str, object]) -> list[dict[str, object]]:
    """Return only dictionary cells so untyped JSON context is safe to inspect."""
    cells = document.get("cells")
    if not isinstance(cells, list):
        return []
    return [cell for cell in cells if isinstance(cell, dict)]
