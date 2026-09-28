"""M0 稳定领域错误。"""


class AgentInfrastructureError(RuntimeError):
    code = "agent_infrastructure_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class PermissionDeniedError(AgentInfrastructureError):
    code = "permission_denied"


class RevisionConflictError(AgentInfrastructureError):
    code = "revision_conflict"


class IdempotencyKeyReusedError(AgentInfrastructureError):
    code = "idempotency_key_reused"


class ArtifactHashMismatchError(AgentInfrastructureError):
    code = "artifact_hash_mismatch"


class DependencyInvalidError(AgentInfrastructureError):
    code = "dependency_invalid"


class AuthorizationRejectedError(AgentInfrastructureError):
    code = "authorization_rejected"


class BudgetExhaustedError(AgentInfrastructureError):
    code = "budget_exhausted"


class InvalidStateTransitionError(AgentInfrastructureError):
    code = "invalid_state_transition"


class RecoveryRequiredError(AgentInfrastructureError):
    code = "recovery_required"
