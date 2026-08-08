"""汇报提纲核心组装、来源边界、导出与版本测试。"""

from datetime import UTC, datetime

import pytest

from app.modules.comparison.shared import SourceRef
from app.modules.paper_analysis.schema import AnalysisField, ClaimKind, StructuredPaperResult
from app.modules.presentation.model import Presentation
from app.modules.presentation.outline_builder import build_single_outline
from app.modules.presentation.schema import OutlineSection, PresentationPatch
from app.modules.presentation.service import PresentationService


def _result() -> StructuredPaperResult:
    field = AnalysisField(value="Evidence-backed statement", kind=ClaimKind.FACT, source_indices=[0])
    return StructuredPaperResult(**{name: field for name in StructuredPaperResult.model_fields})


def test_single_outline_is_complete_and_evidence_bound() -> None:
    source = SourceRef(pmid="123456", locator="paper_analysis_source_0")

    sections = build_single_outline(_result(), {0: source})
    by_title = {section.title: section for section in sections}

    assert {
        "Research background",
        "Scientific question",
        "Study design",
        "Main results",
        "Innovation",
        "Limitations",
        "Discussion questions",
        "Figures to review",
        "Relation to current research topic",
    } <= set(by_title)
    assert by_title["Main results"].evidence == [source]
    assert by_title["Main results"].missing_evidence is False
    assert by_title["Figures to review"].missing_evidence is True
    assert by_title["Relation to current research topic"].content == "待补充课题背景"


def test_missing_identifier_marks_claim_as_missing_evidence() -> None:
    sections = build_single_outline(_result(), {})

    assert all(
        section.missing_evidence
        for section in sections
        if section.title not in {"Figures to review", "Relation to current research topic"}
    )


class _Repository:
    def __init__(self, entity: Presentation) -> None:
        self.entity = entity

    async def get(self, _presentation_id: int) -> Presentation:
        return self.entity

    async def save(self, entity: Presentation) -> Presentation:
        return entity


@pytest.mark.asyncio
async def test_edit_increments_version_and_markdown_exports_current_content() -> None:
    now = datetime.now(UTC)
    entity = Presentation(
        id=1,
        document_ids_json="[1]",
        outline_json='[{"title":"Old","content":"Old","evidence":[],"missing_evidence":true}]',
        version=1,
        created_at=now,
        updated_at=now,
    )
    service = PresentationService.__new__(PresentationService)
    service._repository = _Repository(entity)  # type: ignore[assignment]

    updated = await service.patch(
        1,
        PresentationPatch(
            sections=[OutlineSection(title="Main results", content="Updated", missing_evidence=True)]
        ),
    )
    markdown = await service.export(1)

    assert updated.version == 2
    assert "Version: 2" in markdown
    assert "## Main results" in markdown
    assert "Updated" in markdown
