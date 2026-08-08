"""Unit tests for advisor decision transitions."""

import pytest

from app.common.exceptions import ConflictError
from app.modules.advisor_workflow.state_machine import status_for_decision


def test_all_advisor_decisions_have_explicit_statuses() -> None:
    assert status_for_decision("active", "accept") == "accepted"
    assert status_for_decision("active", "revise") == "active"
    assert status_for_decision("active", "reject") == "rejected"


def test_rejected_direction_cannot_be_revised() -> None:
    with pytest.raises(ConflictError, match="Restore"):
        status_for_decision("rejected", "revise")
