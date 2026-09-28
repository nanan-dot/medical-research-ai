"""Server-owned external execution state machine used by model recovery."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_service import ArtifactService
from app.agents.authorization_model import ModelTransferAuthorizationRecord
from app.agents.contracts import ArtifactRef
from app.agents.enums import EXTERNAL_EXECUTION_TRANSITIONS, ExternalExecutionState
from app.agents.errors import InvalidStateTransitionError, RevisionConflictError
from app.agents.idempotency_model import AgentIdempotencyRecord
from app.agents.model import AgentRunRecord
from app.agents.runtime_model import AgentExternalExecutionRecord, AgentStepRecord


class ExternalExecutionService:
    async def prepare(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        step_id: str,
        attempt: int,
        request_fingerprint: str,
        authorization_id: str,
        reservation_id: str,
        expected_artifact_type: str | None = None,
        expected_artifact_key: str | None = None,
    ) -> AgentExternalExecutionRecord:
        run = await session.get(AgentRunRecord, run_id)
        step = await session.get(AgentStepRecord, step_id)
        if (
            run is None
            or run.research_context_id is None
            or step is None
            or step.run_id != run_id
            or step.attempt != attempt
        ):
            raise ValueError("external execution identity does not match Run/Step")
        if (expected_artifact_type is None) != (expected_artifact_key is None):
            raise ValueError("expected artifact type and key must be supplied together")
        # BEGIN IMMEDIATE 串行化同库写入，唯一约束作为绕过事务协议的最后防线。
        latest_seq = await session.scalar(
            select(func.max(AgentExternalExecutionRecord.execution_seq)).where(
                AgentExternalExecutionRecord.run_id == run_id
            )
        )
        record = AgentExternalExecutionRecord(
            execution_id=str(uuid4()),
            execution_seq=(latest_seq or 0) + 1,
            research_context_id=run.research_context_id,
            run_id=run_id,
            step_id=step_id,
            attempt=attempt,
            request_fingerprint=request_fingerprint,
            input_hash=step.input_hash,
            authorization_id=authorization_id,
            reservation_id=reservation_id,
            expected_artifact_type=expected_artifact_type,
            expected_artifact_key=expected_artifact_key,
            idempotency_record_id=None,
            formal_artifact_id=None,
            state="prepared",
            result_payload_hash=None,
            revision=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        return record

    async def bind_formal_result(
        self,
        session: AsyncSession,
        *,
        execution_id: str,
        expected_revision: int,
        idempotency_record_id: str,
        artifact_ref: ArtifactRef,
    ) -> AgentExternalExecutionRecord:
        execution = await session.get(AgentExternalExecutionRecord, execution_id)
        step = (
            await session.get(AgentStepRecord, execution.step_id)
            if execution is not None
            else None
        )
        idem = await session.get(AgentIdempotencyRecord, idempotency_record_id)
        authorization = (
            await session.get(
                ModelTransferAuthorizationRecord, execution.authorization_id
            )
            if execution is not None
            else None
        )
        if (
            execution is None
            or execution.revision != expected_revision
            or execution.state != "succeeded"
            or not _is_sha256(execution.result_payload_hash)
            or step is None
            or step.run_id != execution.run_id
            or step.attempt != execution.attempt
            or step.input_hash != execution.input_hash
            or idem is None
            or idem.research_context_id != execution.research_context_id
            or idem.action != "formalize_model_result"
            or authorization is None
            or idem.actor_scope != authorization.actor_scope
            or idem.request_hash != execution.request_fingerprint
            or idem.resource_type != "artifact"
            or idem.resource_id != artifact_ref.artifact_id
            or idem.resource_version != artifact_ref.version_key
            or execution.expected_artifact_type != artifact_ref.artifact_type
            or execution.expected_artifact_key != artifact_ref.artifact_key
            or artifact_ref.model_dump(mode="json") not in (step.output_refs_json or [])
        ):
            raise RevisionConflictError("formal result binding does not match execution")
        await ArtifactService().resolve(
            session,
            artifact_ref,
            research_context_id=execution.research_context_id,
        )
        execution.idempotency_record_id = idempotency_record_id
        execution.formal_artifact_id = artifact_ref.artifact_id
        execution.revision += 1
        await session.flush()
        return execution

    async def transition(
        self,
        session: AsyncSession,
        *,
        execution_id: str,
        expected_revision: int,
        expected_state: str,
        next_state: str,
        result_payload_hash: str | None = None,
    ) -> AgentExternalExecutionRecord:
        try:
            current = ExternalExecutionState(expected_state)
            target = ExternalExecutionState(next_state)
        except ValueError as exc:
            raise InvalidStateTransitionError(
                f"unknown external execution state: {expected_state} -> {next_state}"
            ) from exc
        if target not in EXTERNAL_EXECUTION_TRANSITIONS[current]:
            raise InvalidStateTransitionError(
                f"external execution transition rejected: {current} -> {target}"
            )
        if target == ExternalExecutionState.SUCCEEDED:
            if not _is_sha256(result_payload_hash):
                raise InvalidStateTransitionError(
                    "succeeded requires a lowercase SHA-256 result payload hash"
                )
        elif result_payload_hash is not None:
            raise InvalidStateTransitionError(
                "result payload hash is only valid for succeeded"
            )
        result = await session.execute(
            update(AgentExternalExecutionRecord)
            .where(
                AgentExternalExecutionRecord.execution_id == execution_id,
                AgentExternalExecutionRecord.revision == expected_revision,
                AgentExternalExecutionRecord.state == expected_state,
            )
            .values(
                state=next_state,
                result_payload_hash=result_payload_hash,
                revision=AgentExternalExecutionRecord.revision + 1,
                updated_at=datetime.now(UTC),
            )
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError("external execution state changed")
        record = await session.get(AgentExternalExecutionRecord, execution_id)
        assert record is not None
        await session.refresh(record)
        return record


def _is_sha256(value: str | None) -> bool:
    if value is None or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
