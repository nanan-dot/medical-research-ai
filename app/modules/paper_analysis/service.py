"""Orchestrate evidence-grounded analysis of one indexed paper."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.integrations.paperqa2 import PaperQA2Client, PaperQAIndex, create_paperqa2_client
from app.integrations.paperqa2.exceptions import PaperQA2Error
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import IndexStatus
from app.modules.document.service import sanitize_error_message
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_analysis.prompts import FIELD_NAMES, TEMPLATE_VERSION, build_analysis_prompt
from app.modules.paper_analysis.repository import PaperAnalysisRepository
from app.modules.paper_analysis.schema import (
    AnalysisField,
    AnalysisStatus,
    PaperAnalysisCorrection,
    PaperAnalysisRead,
    StructuredPaperResult,
)


class PaperAnalysisService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], PaperQA2Client] | None = None,
    ) -> None:
        self.repo = PaperAnalysisRepository(session)
        self.documents = DocumentRepository(session)
        self.client_factory = client_factory or create_paperqa2_client

    async def create(self, document_id: int) -> PaperAnalysisRead:
        document = await self._require_indexed_document(document_id)
        now = datetime.now(UTC)
        entity = await self.repo.create(
            PaperAnalysis(
                document_id=document.id,
                analysis_status=AnalysisStatus.PENDING.value,
                template_version=TEMPLATE_VERSION,
                model_version=self._model_version(),
                generation=1,
                created_at=now,
                updated_at=now,
            )
        )
        return await self._generate(entity, document.paperqa_index_key or "")

    async def get(self, id: int) -> PaperAnalysisRead:
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Paper analysis not found: {id}")
        return self._read(entity)

    async def regenerate(self, id: int) -> PaperAnalysisRead:
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Paper analysis not found: {id}")
        document = await self._require_indexed_document(entity.document_id)
        entity.generation += 1
        entity.template_version = TEMPLATE_VERSION
        entity.model_version = self._model_version()
        return await self._generate(entity, document.paperqa_index_key or "")

    async def correct(self, id: int, correction: PaperAnalysisCorrection) -> PaperAnalysisRead:
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Paper analysis not found: {id}")
        if correction.field_name not in FIELD_NAMES:
            raise ConflictError("Unknown analysis field")
        result = self._result(entity)
        sources = self._sources(entity)
        self._validate_source_indices(correction.source_indices, len(sources))
        setattr(
            result,
            correction.field_name,
            AnalysisField.model_validate({
                "value": correction.value,
                "kind": correction.kind,
                "source_indices": correction.source_indices,
            }),
        )
        entity.structured_result = result.model_dump_json()
        entity.pending_confirmations = json.dumps(
            [item for item in self._pending(entity) if item != correction.field_name]
        )
        entity.updated_at = datetime.now(UTC)
        await self.repo.save(entity)
        return self._read(entity)

    async def export_markdown(self, id: int) -> str:
        analysis = await self.get(id)
        if analysis.structured_result is None:
            raise ConflictError("Paper analysis has no completed result")
        lines = [f"# 单篇论文分析 #{analysis.id}", ""]
        for name in FIELD_NAMES:
            field = getattr(analysis.structured_result, name)
            references = ", ".join(f"来源 {index + 1}" for index in field.source_indices)
            lines.extend([f"## {name}", "", field.value, ""])
            if references:
                lines.extend([f"证据：{references}", ""])
        lines.extend(["## 来源", ""])
        for position, source in enumerate(analysis.sources, 1):
            pages = f" pp. {source.page_start}-{source.page_end}" if source.page_start else ""
            lines.append(f"{position}. {source.citation or source.title or '未命名来源'}{pages}")
        return "\n".join(lines).strip() + "\n"

    async def _generate(self, entity: PaperAnalysis, index_key: str) -> PaperAnalysisRead:
        entity.analysis_status = AnalysisStatus.ANALYZING.value
        entity.error_code = None
        entity.error_message = None
        entity.updated_at = datetime.now(UTC)
        await self.repo.save(entity)
        try:
            answer = await self.client_factory().ask(
                PaperQAIndex(index_id=index_key, document_count=1, reused=True),
                build_analysis_prompt(),
            )
            payload = json.loads(answer.answer)
            result = StructuredPaperResult.model_validate(payload)
            for name in FIELD_NAMES:
                self._validate_source_indices(
                    getattr(result, name).source_indices, len(answer.sources)
                )
        except (PaperQA2Error, json.JSONDecodeError, ValidationError, ValueError) as exc:
            entity.analysis_status = AnalysisStatus.FAILED.value
            entity.error_code = getattr(exc, "code", "analysis_response_invalid")
            entity.error_message = sanitize_error_message(str(exc))
            entity.updated_at = datetime.now(UTC)
            await self.repo.save(entity)
            raise ConflictError("Paper analysis failed") from exc
        entity.structured_result = result.model_dump_json()
        entity.sources = json.dumps([source.model_dump(mode="json") for source in answer.sources])
        pending = [name for name in FIELD_NAMES if getattr(result, name).kind == "not_found"]
        entity.pending_confirmations = json.dumps(pending)
        entity.analysis_status = AnalysisStatus.SUCCEEDED.value
        entity.updated_at = datetime.now(UTC)
        await self.repo.save(entity)
        return self._read(entity)

    async def _require_indexed_document(self, document_id: int):
        document = await self.documents.get(document_id)
        if document is None:
            raise NotFoundError(f"Document not found: {document_id}")
        if document.index_status != IndexStatus.SUCCEEDED.value or not document.paperqa_index_key:
            raise ConflictError("Document must have a current successful index")
        return document

    @staticmethod
    def _validate_source_indices(indices: list[int], source_count: int) -> None:
        if any(index < 0 or index >= source_count for index in indices):
            raise ValueError("Analysis field references an unavailable source")

    def _read(self, entity: PaperAnalysis) -> PaperAnalysisRead:
        return PaperAnalysisRead(
            id=entity.id,
            document_id=entity.document_id,
            analysis_status=AnalysisStatus(entity.analysis_status),
            template_version=entity.template_version,
            model_version=entity.model_version,
            generation=entity.generation,
            structured_result=self._result(entity) if entity.structured_result else None,
            sources=self._sources(entity),
            pending_confirmations=self._pending(entity),
            error_code=entity.error_code,
            error_message=entity.error_message,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _result(entity: PaperAnalysis) -> StructuredPaperResult:
        return StructuredPaperResult.model_validate_json(entity.structured_result or "{}")

    @staticmethod
    def _sources(entity: PaperAnalysis):
        from app.integrations.paperqa2 import PaperSource

        return [PaperSource.model_validate(item) for item in json.loads(entity.sources or "[]")]

    @staticmethod
    def _pending(entity: PaperAnalysis) -> list[str]:
        return list(json.loads(entity.pending_confirmations or "[]"))

    @staticmethod
    def _model_version() -> str:
        models = {
            "openai": settings.OPENAI_MODEL,
            "openrouter": settings.OPENROUTER_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }
        return f"{settings.DEFAULT_MODEL_PROVIDER}:{models[settings.DEFAULT_MODEL_PROVIDER] or 'unconfigured'}"
