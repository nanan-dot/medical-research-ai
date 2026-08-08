"""把已有论文分析/比较结果组装成汇报提纲的纯函数。"""

from app.modules.comparison.schema import ComparisonTaskRead
from app.modules.comparison.shared import SourceRef
from app.modules.paper_analysis.schema import StructuredPaperResult
from app.modules.presentation.schema import OutlineSection


def build_single_outline(
    result: StructuredPaperResult,
    evidence_by_index: dict[int, SourceRef],
) -> list[OutlineSection]:
    mapping = [
        ("Research background", result.research_background),
        ("Scientific question", result.research_question),
        ("Study design", result.study_type),
        ("Main results", result.main_results),
        ("Innovation", result.innovations),
        ("Limitations", result.limitations),
        ("Discussion questions", result.next_questions),
    ]
    sections = []
    for title, field in mapping:
        evidence = [
            evidence_by_index[index]
            for index in field.source_indices
            if index in evidence_by_index
        ]
        sections.append(
            OutlineSection(
                title=title,
                content=field.value,
                evidence=evidence,
                missing_evidence=not evidence,
            )
        )
    return _required_tail(sections)


def build_comparison_outline(task: ComparisonTaskRead) -> list[OutlineSection]:
    sections = [
        OutlineSection(
            title=f"{cell.field.value}: document {cell.document_id}",
            content=cell.cell_value,
            evidence=cell.sources,
            missing_evidence=not cell.sources,
        )
        for cell in task.cells
    ]
    return _required_tail(sections)


def _required_tail(sections: list[OutlineSection]) -> list[OutlineSection]:
    return sections + [
        OutlineSection(
            title="Figures to review",
            content="⚠️ Figures were not parsed; review the original Figure/Table manually.",
            missing_evidence=True,
        ),
        OutlineSection(
            title="Relation to current research topic",
            content="待补充课题背景",
            missing_evidence=True,
        ),
    ]
