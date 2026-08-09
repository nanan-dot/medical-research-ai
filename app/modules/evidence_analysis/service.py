"""Application service for matrix-based two-tier evidence analysis."""

import json
from collections.abc import Awaitable, Callable

from pydantic import AnyHttpUrl, SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AIModelError, ConflictError, NotFoundError
from app.core.security import SecretCipher
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage, LLMConfig
from app.integrations.ollama.client import OllamaClient
from app.modules.comparison.shared import SourceRef
from app.modules.evidence_analysis.interpretation import parse_grounded_interpretation
from app.modules.evidence_analysis.prompts import build_interpretation_prompt
from app.modules.evidence_analysis.repository import EvidenceAnalysisRepository
from app.modules.evidence_analysis.schema import (
    AnalysisMetadata,
    EvidenceAnalysisRead,
    EvidenceAnalysisRequest,
    ResearchTypeStatisticRead,
    StatisticsLayerRead,
    TopicStatisticRead,
)
from app.modules.evidence_analysis.statistics import (
    StatisticalDocument,
    calculate_research_type_distribution,
    calculate_topic_statistics,
)
from app.modules.evidence_matrix.model import MatrixCell, MatrixDocument
from app.modules.library_item.model import LibraryItem
from app.modules.model_config.model import ModelConfig
from app.modules.model_config.repository import ModelConfigRepository

InterpretationGenerator = Callable[[str, int | None, bool], Awaitable[str]]


class EvidenceAnalysisService:
    """Build deterministic matrix statistics before requesting any model interpretation."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        interpretation_generator: InterpretationGenerator | None = None,
    ) -> None:
        self._repository = EvidenceAnalysisRepository(session)
        self._model_configs = ModelConfigRepository(session)
        self._interpretation_generator = (
            interpretation_generator or self._generate_with_routed_model
        )

    async def analyze(self, request: EvidenceAnalysisRequest) -> EvidenceAnalysisRead:
        matrix = await self._repository.get_matrix(request.matrix_id)
        if matrix is None:
            raise NotFoundError(f"Evidence matrix not found: {request.matrix_id}")
        documents = await self._repository.list_documents(matrix.id)
        if not documents:
            raise ConflictError(
                "Evidence matrix is empty; create a matrix with literature before analysis"
            )
        cells = await self._repository.list_cells(matrix.id)
        library_items = await self._repository.list_library_items_for_documents(
            [document.document_id for document in documents]
        )
        statistical_documents, sources = _normalize_documents(
            documents, cells, library_items, request.topic_field_keys
        )
        statistics = _build_statistics(statistical_documents)
        prompt = build_interpretation_prompt(
            statistics,
            _source_catalog(sources),
            _build_evidence_context(documents, cells, request.topic_field_keys),
            request.retrieval_scope,
            request.retrieval_date.isoformat(),
        )
        try:
            raw_interpretation = await self._interpretation_generator(
                prompt,
                request.model_config_id,
                any(document.user_notes.strip() for document in documents),
            )
            interpretation = parse_grounded_interpretation(
                raw_interpretation, statistics, sources
            )
        except (ValidationError, ValueError) as error:
            raise AIModelError(
                "The configured model returned an invalid or ungrounded evidence interpretation"
            ) from error
        return EvidenceAnalysisRead(
            metadata=AnalysisMetadata(
                retrieval_scope=request.retrieval_scope,
                retrieval_date=request.retrieval_date,
                matrix_version=matrix.version,
                document_count=len(documents),
            ),
            statistics=statistics,
            interpretation=interpretation,
        )

    async def _generate_with_routed_model(
        self, prompt: str, model_config_id: int | None, has_private_notes: bool
    ) -> str:
        config = await self._resolve_model_config(model_config_id, has_private_notes)
        messages = [ChatMessage(role="user", content=prompt)]
        if config.provider == "ollama":
            async with OllamaClient(
                base_url=config.api_base, model=config.model_name
            ) as client:
                return (await client.chat(messages)).text
        api_key = SecretCipher().decrypt(config.encrypted_api_key or "")
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model_name,
            api_base=AnyHttpUrl(config.api_base),
            api_key=SecretStr(api_key),
            timeout_seconds=60,
        )
        async with LLMClient(llm_config) as client:
            return (await client.chat(messages)).text

    async def _resolve_model_config(
        self, model_config_id: int | None, has_private_notes: bool
    ) -> ModelConfig:
        if model_config_id is not None:
            config = await self._model_configs.get(model_config_id)
            if config is None:
                raise NotFoundError(f"Model config not found: {model_config_id}")
            if config.provider != "ollama" and not config.allow_cloud_content:
                raise ConflictError(
                    "Cloud evidence analysis requires explicit content-transfer authorization"
                )
            return config
        if has_private_notes:
            local_configs = [
                config
                for config in await self._model_configs.list()
                if config.provider == "ollama"
            ]
            default_config = next(
                (config for config in local_configs if config.is_default), None
            )
            if default_config is not None:
                return default_config
            if local_configs:
                return local_configs[0]
            raise ConflictError(
                "No local model is configured for private notes; install Ollama or explicitly select a cloud model"
            )
        cloud_configs = [
            config
            for config in await self._model_configs.list()
            if config.provider != "ollama" and config.allow_cloud_content
        ]
        default_config = next(
            (config for config in cloud_configs if config.is_default), None
        )
        if default_config is not None:
            return default_config
        if cloud_configs:
            return cloud_configs[0]
        raise ConflictError(
            "No model is configured for public evidence analysis; configure a cloud API key or select Ollama explicitly"
        )


def _normalize_documents(
    documents: list[MatrixDocument],
    cells: list[MatrixCell],
    library_items: list[LibraryItem],
    topic_field_keys: list[str],
) -> tuple[list[StatisticalDocument], list[SourceRef]]:
    items_by_document = {
        item.document_id: item for item in library_items if item.document_id is not None
    }
    cells_by_document: dict[int, list] = {}
    for cell in cells:
        cells_by_document.setdefault(cell.document_id, []).append(cell)
    normalized: list[StatisticalDocument] = []
    sources: list[SourceRef] = []
    for document in documents:
        item = items_by_document.get(document.document_id)
        matching_cells = cells_by_document.get(document.document_id, [])
        cell_values = {cell.field_key: cell.cell_value for cell in matching_cells}
        research_type = cell_values.get("study_type")
        topics = tuple(
            cell_values[key] for key in topic_field_keys if cell_values.get(key)
        )
        normalized.append(
            StatisticalDocument(
                document.document_id, item.year if item else None, research_type, topics
            )
        )
        sources.extend(_cell_sources(matching_cells))
        if item is not None:
            sources.append(
                SourceRef(pmid=item.pmid, doi=item.doi, locator="library_item")
            )
    unique_sources = {
        (_source.pmid, _source.doi, _source.locator): _source for _source in sources
    }
    return normalized, list(unique_sources.values())


def _cell_sources(cells: list[MatrixCell]) -> list[SourceRef]:
    sources: list[SourceRef] = []
    for cell in cells:
        try:
            sources.extend(
                SourceRef.model_validate(item) for item in json.loads(cell.sources)
            )
        except (json.JSONDecodeError, ValidationError):
            continue
    return sources


def _build_statistics(documents: list[StatisticalDocument]) -> StatisticsLayerRead:
    topics = [
        TopicStatisticRead(**item.__dict__)
        for item in calculate_topic_statistics(documents)
    ]
    return StatisticsLayerRead(
        high_frequency_topics=topics,
        recent_growth_topics=[item for item in topics if item.trend == "up"],
        research_type_distribution=[
            ResearchTypeStatisticRead(
                research_type=item.research_type, count=item.count, basis=item.basis
            )
            for item in calculate_research_type_distribution(documents)
        ],
    )


def _build_evidence_context(
    documents: list[MatrixDocument],
    cells: list[MatrixCell],
    topic_field_keys: list[str],
) -> list[dict[str, object]]:
    cells_by_document: dict[int, list[MatrixCell]] = {}
    for cell in cells:
        cells_by_document.setdefault(cell.document_id, []).append(cell)
    context: list[dict[str, object]] = []
    allowed_keys = {
        *topic_field_keys,
        "study_type",
        "results",
        "limitations",
        "methods",
    }
    for document in documents:
        values = {
            cell.field_key: cell.cell_value
            for cell in cells_by_document.get(document.document_id, [])
            if cell.field_key in allowed_keys and cell.cell_value != "缺失"
        }
        context.append(
            {
                "document_id": document.document_id,
                "matrix_fields": values,
                "user_note": document.user_notes or None,
            }
        )
    return context


def _source_catalog(sources: list[SourceRef]) -> list[dict[str, object]]:
    return [source.model_dump(exclude_none=True) for source in sources]
