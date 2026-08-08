import json
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.exceptions import ConflictError, NotFoundError
from app.modules.comparison.service import ComparisonService
from app.modules.paper_analysis.repository import PaperAnalysisRepository
from app.modules.paper_analysis.schema import StructuredPaperResult
from app.modules.presentation.model import Presentation
from app.modules.presentation.repository import PresentationRepository
from app.modules.presentation.schema import (
    OutlineSection,
    PresentationCreate,
    PresentationPatch,
    PresentationRead,
)


class PresentationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = PresentationRepository(session)
        self._analyses = PaperAnalysisRepository(session)
        self._comparison = ComparisonService(session)

    async def create(self, payload: PresentationCreate) -> PresentationRead:
        sections = await self._build_sections(payload)
        entity = Presentation(
            document_ids_json=json.dumps(payload.document_ids),
            outline_json=json.dumps([section.model_dump() for section in sections]),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return self._read(await self._repository.create(entity))

    async def get(self, presentation_id: int) -> PresentationRead:
        return self._read(await self._entity(presentation_id))

    async def patch(self, presentation_id: int, payload: PresentationPatch) -> PresentationRead:
        entity = await self._entity(presentation_id)
        entity.outline_json = json.dumps([section.model_dump() for section in payload.sections])
        entity.version += 1
        entity.updated_at = datetime.now(UTC)
        return self._read(await self._repository.save(entity))

    async def export(self, presentation_id: int) -> str:
        presentation = await self.get(presentation_id)
        lines = [
            f"# Group meeting presentation {presentation.id}",
            f"Version: {presentation.version}",
            "",
        ]
        for section in presentation.sections:
            lines.extend([f"## {section.title}", section.content, ""])
        return "\n".join(lines)

    async def _build_sections(self, payload: PresentationCreate) -> list[OutlineSection]:
        if payload.comparison_id:
            return await self._comparison_sections(payload.comparison_id)
        analysis = await self._analyses.latest_for_document(payload.document_ids[0])
        if analysis is None or not analysis.structured_result:
            raise ConflictError("Run paper analysis before creating a presentation")
        result = StructuredPaperResult.model_validate_json(analysis.structured_result)
        sources = json.loads(analysis.sources or "[]")
        mapping = [
            ("Research background", result.research_background),
            ("Scientific question", result.research_question),
            ("Study design", result.study_type),
            ("Main results", result.main_results),
            ("Innovation", result.innovations),
            ("Limitations", result.limitations),
            ("Discussion questions", result.next_questions),
        ]
        sections = [
            OutlineSection(
                title=name, content=field.value, missing_evidence=not field.source_indices
            )
            for name, field in mapping
        ]
        sections.append(
            OutlineSection(
                title="Figures to review",
                content="⚠️ Figures were not parsed; review the original figures/tables manually.",
                missing_evidence=True,
            )
        )
        sections.append(
            OutlineSection(
                title="Original sources",
                content=", ".join(
                    item.get("citation") or item.get("title") or "source" for item in sources
                ),
                missing_evidence=not sources,
            )
        )
        return sections

    async def _comparison_sections(self, comparison_id: int) -> list[OutlineSection]:
        task = await self._comparison.get(comparison_id)
        return [
            OutlineSection(
                title=f"{cell.field.value}: document {cell.document_id}",
                content=cell.cell_value,
                evidence=cell.sources,
                missing_evidence=not cell.sources,
            )
            for cell in task.cells
        ] + [
            OutlineSection(
                title="Figures to review",
                content="⚠️ Figures were not parsed; review the original figures/tables manually.",
                missing_evidence=True,
            )
        ]

    async def _entity(self, presentation_id: int) -> Presentation:
        entity = await self._repository.get(presentation_id)
        if entity is None:
            raise NotFoundError(f"Presentation not found: {presentation_id}")
        return entity

    @staticmethod
    def _read(entity: Presentation) -> PresentationRead:
        return PresentationRead(
            id=entity.id,
            document_ids=json.loads(entity.document_ids_json),
            sections=json.loads(entity.outline_json),
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
