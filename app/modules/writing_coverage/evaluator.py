"""Pure conservative rules for writing-project evidence coverage."""

from app.modules.writing_coverage.schema import ParagraphCoverage, PublishReadinessRead
from app.modules.writing_project.schema import (
    GeneratedContent,
    WritingEvidenceReferenceRead,
)


def evaluate_coverage(
    content: GeneratedContent,
    references: list[WritingEvidenceReferenceRead],
    has_unconfirmed_suggestions: bool,
) -> PublishReadinessRead:
    """Build readiness from persisted links rather than semantic or keyword guesses."""
    reference_ids = {item.segment_id for item in references}
    pending_ids = {
        item.id for item in content.pending_items if item.status == "pending"
    }
    paragraphs = [
        _evaluate_segment(segment, reference_ids, pending_ids)
        for segment in content.segments
    ]
    blockers = [blocker for item in paragraphs for blocker in item.blockers]
    warnings = [warning for item in paragraphs for warning in item.warnings]
    if has_unconfirmed_suggestions:
        blockers.append(
            "Unconfirmed AI suggestions must not be exported as final content"
        )
    return PublishReadinessRead(
        passed=not blockers, blockers=blockers, warnings=warnings, paragraphs=paragraphs
    )


def _evaluate_segment(
    segment, reference_ids: set[str], pending_ids: set[str]
) -> ParagraphCoverage:
    if segment.pending_item_id in pending_ids or segment.origin in {
        "pending",
        "model_inference",
    }:
        return ParagraphCoverage(
            segment_id=segment.id,
            status="needs_verification",
            blockers=[f"Segment {segment.id} contains a pending or inferred claim"],
        )
    if (
        segment.origin in {"paper_evidence", "model_summary"}
        and segment.id not in reference_ids
    ):
        return ParagraphCoverage(
            segment_id=segment.id,
            status="missing_citation",
            blockers=[f"Segment {segment.id} has no persisted evidence reference"],
        )
    return ParagraphCoverage(segment_id=segment.id, status="supported")
