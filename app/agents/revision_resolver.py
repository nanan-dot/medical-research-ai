"""Authoritative resolver for mutable revisions bound to a confirmation."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.authorization_model import ModelTransferAuthorizationRecord
from app.agents.confirmation_model import AgentRoleQualificationRecord
from app.agents.errors import RevisionConflictError
from app.agents.model import AgentRunRecord
from app.agents.runtime_model import AgentStepRecord

RevisionRecord = (
    AgentRunRecord | AgentStepRecord | ModelTransferAuthorizationRecord
    | AgentRoleQualificationRecord
)

REVISION_TYPES: dict[str, type[RevisionRecord]] = {
    "run": AgentRunRecord,
    "step": AgentStepRecord,
    "authorization": ModelTransferAuthorizationRecord,
    "qualification": AgentRoleQualificationRecord,
}


class RevisionResolver:
    async def assert_current(
        self, session: AsyncSession, expected_revisions: dict[str, int]
    ) -> None:
        for binding, expected in sorted(expected_revisions.items()):
            kind, separator, record_id = binding.partition(":")
            model = REVISION_TYPES.get(kind)
            if not separator or not record_id or model is None or expected < 1:
                raise ValueError(f"unsupported revision binding: {binding}")
            record = await session.get(model, record_id)
            if not isinstance(record, (
                AgentRunRecord, AgentStepRecord,
                ModelTransferAuthorizationRecord, AgentRoleQualificationRecord,
            )) or int(record.revision) != int(expected):
                raise RevisionConflictError(f"revision changed: {binding}")
