"""Pure state transitions for advisor decisions."""

from app.common.exceptions import ConflictError
from app.modules.advisor_workflow.schema import Decision

ACTIVE_STATUS = "active"
ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"


def status_for_decision(current_status: str, decision: Decision) -> str:
    """Return the valid direction status for a recorded advisor decision."""
    if current_status == "merged":
        raise ConflictError("Merged directions cannot receive advisor decisions")
    if current_status == REJECTED_STATUS and decision == "revise":
        raise ConflictError("Restore a rejected direction before creating a revision")
    if decision == "accept":
        return ACCEPTED_STATUS
    if decision == "reject":
        return REJECTED_STATUS
    return ACTIVE_STATUS
