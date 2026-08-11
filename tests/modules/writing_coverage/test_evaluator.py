"""Given/When/Then acceptance tests for publish-readiness rules."""

from app.modules.writing_coverage.evaluator import evaluate_coverage
from app.modules.writing_project.schema import (
    ContentSegment,
    GeneratedContent,
    WritingEvidenceReferenceRead,
)


def test_given_missing_reference_and_pending_claim_when_checked_then_export_is_blocked() -> (
    None
):
    content = GeneratedContent(
        segments=[
            ContentSegment(
                id="missing", text="Evidence claim", origin="paper_evidence"
            ),
            ContentSegment(id="pending", text="Unverified claim", origin="pending"),
        ]
    )
    result = evaluate_coverage(content, [], has_unconfirmed_suggestions=True)
    assert result.passed is False
    assert {item.status for item in result.paragraphs} == {
        "missing_citation",
        "needs_verification",
    }
    assert len(result.blockers) == 3


def test_given_persisted_reference_when_checked_then_evidence_segment_is_supported() -> (
    None
):
    content = GeneratedContent(
        segments=[
            ContentSegment(
                id="supported", text="Evidence claim", origin="paper_evidence"
            )
        ]
    )
    reference = WritingEvidenceReferenceRead(
        id=1,
        segment_id="supported",
        source_type="document",
        document_id=1,
        conversation_citation_id=None,
        matrix_cell_id=None,
        page=None,
        section=None,
        evidence_text=None,
        citation_text="Local document",
        pmid=None,
        doi=None,
        locator=None,
    )
    result = evaluate_coverage(content, [reference], has_unconfirmed_suggestions=False)
    assert result.passed is True
    assert result.paragraphs[0].status == "supported"
