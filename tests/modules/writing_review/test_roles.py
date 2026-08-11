"""Given/When/Then tests for detailed simulated-reviewer constraints."""

import pytest

from app.modules.writing_review.roles import ROLE_CONSTRAINTS
from app.modules.writing_review.schema import WritingReviewRequest


def test_given_presets_when_loaded_then_all_six_roles_have_expertise_focus_and_prohibitions() -> (
    None
):
    assert len(ROLE_CONSTRAINTS) == 6
    assert all(
        item.expertise and item.focus and item.prohibited
        for item in ROLE_CONSTRAINTS.values()
    )


def test_given_no_or_two_role_types_when_requested_then_review_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        WritingReviewRequest(
            expected_version=1,
            segment_ids=["s"],
            evidence_reference_ids=[1],
            model_config_id=1,
        )
