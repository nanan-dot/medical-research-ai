"""Given/When/Then acceptance tests for evidence-bound writing P0."""

import pytest

from app.modules.writing_ai.schema import EvidenceInput, WritingGenerationRequest


def test_given_no_evidence_when_building_a_draft_then_request_is_rejected() -> None:
    with pytest.raises(ValueError, match="evidence"):
        WritingGenerationRequest(
            expected_version=1,
            task="draft",
            evidence=[],
        )


def test_given_evidence_when_building_a_draft_then_evidence_identifiers_are_required() -> None:
    request = WritingGenerationRequest(
        expected_version=1,
        task="draft",
        evidence=[EvidenceInput(reference_id=2, text="Observed result.")],
    )
    assert request.evidence[0].reference_id == 2
