"""M0 公共状态枚举。

这里集中维护公共状态，领域 Agent 只能在自己的 payload 中保存领域状态。
"""

from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_USER_INPUT = "awaiting_user_input"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RECOVERY_REQUIRED = "recovery_required"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    CANCELLED_AFTER_COMMIT = "cancelled_after_commit"


class StepStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_USER_INPUT = "awaiting_user_input"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ArtifactValidityStatus(StrEnum):
    VALID = "valid"
    STALE = "stale"
    NEEDS_REVALIDATION = "needs_revalidation"
    SUPERSEDED = "superseded"
    INVALID = "invalid"


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    CONSUMED = "consumed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class AuthorizationStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ExternalExecutionState(StrEnum):
    PREPARED = "prepared"
    SENT = "sent"
    SUCCEEDED = "succeeded"
    FAILED_BEFORE_SEND = "failed_before_send"
    OUTCOME_UNKNOWN = "outcome_unknown"


class DependencyKind(StrEnum):
    SOURCE = "source"
    INPUT = "input"
    PROFILE = "profile"
    DERIVED = "derived"


TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.COMPLETED,
        RunStatus.PARTIAL,
        RunStatus.FAILED,
        RunStatus.REJECTED,
        RunStatus.CANCELLED,
        RunStatus.CANCELLED_AFTER_COMMIT,
    }
)

EXTERNAL_EXECUTION_TRANSITIONS = {
    ExternalExecutionState.PREPARED: frozenset(
        {ExternalExecutionState.SENT, ExternalExecutionState.FAILED_BEFORE_SEND}
    ),
    ExternalExecutionState.SENT: frozenset(
        {ExternalExecutionState.SUCCEEDED, ExternalExecutionState.OUTCOME_UNKNOWN}
    ),
    ExternalExecutionState.SUCCEEDED: frozenset(),
    ExternalExecutionState.FAILED_BEFORE_SEND: frozenset(),
    ExternalExecutionState.OUTCOME_UNKNOWN: frozenset(),
}

PUBLIC_EVENT_TYPES = frozenset(
    {
        "run.created",
        "run.status_changed",
        "step.status_changed",
        "artifact.created",
        "artifact.invalidated",
        "confirmation.requested",
        "confirmation.recorded",
        "confirmation.superseded",
        "budget.reserved",
        "budget.settled",
        "export.prepared",
        "export.completed",
        "error.raised",
    }
)
