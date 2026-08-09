import json
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.exceptions import ConflictError, NotFoundError
from app.modules.comparison.service import ComparisonService
from app.modules.comparison.shared import SourceRef
from app.modules.paper_analysis.repository import PaperAnalysisRepository
from app.modules.paper_analysis.schema import StructuredPaperResult
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.presentation.model import Presentation
from app.modules.presentation.outline_builder import (
    build_comparison_outline,
    build_single_outline,
)
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
        self._library = LibraryItemRepository(session)
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

    async def patch(
        self, presentation_id: int, payload: PresentationPatch
    ) -> PresentationRead:
        entity = await self._entity(presentation_id)
        entity.outline_json = json.dumps(
            [section.model_dump() for section in payload.sections]
        )
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

    async def _build_sections(
        self, payload: PresentationCreate
    ) -> list[OutlineSection]:
        if payload.comparison_id:
            try:
                return await self._comparison_sections(payload.comparison_id)
            except NotFoundError:
                # 比较任务缺失时逐篇复用现有单篇分析，而不是重做一套比较逻辑。
                sections: list[OutlineSection] = []
                for document_id in payload.document_ids:
                    sections.extend(await self._single_sections(document_id))
                return sections
        return await self._single_sections(payload.document_ids[0])

    async def _single_sections(self, document_id: int) -> list[OutlineSection]:
        analysis = await self._analyses.latest_for_document(document_id)
        if analysis is None or not analysis.structured_result:
            raise ConflictError("Run paper analysis before creating a presentation")
        result = StructuredPaperResult.model_validate_json(analysis.structured_result)
        items = await self._library.list_items(0, 1000, None)
        item = next(
            (candidate for candidate in items if candidate.document_id == document_id),
            None,
        )
        evidence_by_index = {}
        if item is not None and (item.pmid or item.doi):
            evidence_by_index = {
                index: SourceRef(
                    pmid=item.pmid,
                    doi=item.doi,
                    locator=f"paper_analysis_source_{index}",
                )
                for index, _source in enumerate(json.loads(analysis.sources or "[]"))
            }
        sections = build_single_outline(result, evidence_by_index)
        all_evidence = [source for section in sections for source in section.evidence]
        sections.append(
            OutlineSection(
                title="Original sources",
                content=", ".join(
                    sorted({source.pmid or source.doi or "" for source in all_evidence})
                )
                or "No verified PMID/DOI available",
                evidence=list(
                    {
                        source.model_dump_json(): source for source in all_evidence
                    }.values()
                ),
                missing_evidence=not all_evidence,
            )
        )
        return sections

    async def _comparison_sections(self, comparison_id: int) -> list[OutlineSection]:
        task = await self._comparison.get(comparison_id)
        return build_comparison_outline(task)

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
