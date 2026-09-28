"""Recovery reconciles one exact server-owned execution authority chain."""

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_service import ArtifactService
from app.agents.authorization_model import ModelTransferAuthorizationRecord
from app.agents.budget_model import AgentBudgetReservationRecord, AgentRootBudgetRecord
from app.agents.budget_service import BudgetService
from app.agents.contracts import ArtifactRef
from app.agents.enums import (
    ArtifactValidityStatus,
    AuthorizationStatus,
    RunStatus,
    StepStatus,
)
from app.agents.errors import RecoveryRequiredError, RevisionConflictError
from app.agents.external_execution_service import _is_sha256
from app.agents.idempotency_model import AgentIdempotencyRecord
from app.agents.model import AgentRunRecord
from app.agents.run_runtime_service import RunRuntimeService
from app.agents.runtime_model import AgentExternalExecutionRecord, AgentStepRecord


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class RecoveryService:
    def __init__(
        self,
        runs: RunRuntimeService | None = None,
        artifacts: ArtifactService | None = None,
    ) -> None:
        self._runs = runs or RunRuntimeService()
        self._artifacts = artifacts or ArtifactService()

    async def recover(
        self, session: AsyncSession, *, run_id: str, expected_revision: int
    ) -> AgentRunRecord:
        run = await session.get(AgentRunRecord, run_id)
        if run is None:
            raise KeyError(run_id)
        if run.revision != expected_revision:
            raise RevisionConflictError()
        execution = await session.scalar(
            select(AgentExternalExecutionRecord)
            .where(AgentExternalExecutionRecord.run_id == run_id)
            .order_by(
                desc(AgentExternalExecutionRecord.execution_seq),
            )
            .limit(1)
        )
        if execution is None:
            return await self._resume_new_attempt(session, run, None, None)
        step, reservation = await self._assert_execution_authority(
            session, run, execution
        )
        if await self._has_exact_formal_output(session, run, step, execution, reservation):
            return await self._runs.transition_run(
                session,
                run_id=run_id,
                expected_revision=expected_revision,
                next_status=RunStatus.COMPLETED,
                reason_code="reconciled_exact_formal_output",
            )
        if execution.state in {"prepared", "failed_before_send"}:
            return await self._resume_new_attempt(session, run, step, reservation)
        raise RecoveryRequiredError(
            "latest external execution has no exact formal artifact binding"
        )

    async def _resume_new_attempt(
        self,
        session: AsyncSession,
        run: AgentRunRecord,
        prior_step: AgentStepRecord | None,
        reservation: AgentBudgetReservationRecord | None,
    ) -> AgentRunRecord:
        if reservation is not None and reservation.status == "active":
            await BudgetService().release(
                session, reservation_id=reservation.reservation_id
            )
        if prior_step is not None:
            await self._runs.create_step(
                session,
                run_id=run.run_id,
                step_kind=prior_step.step_kind,
                attempt=prior_step.attempt + 1,
                input_hash=prior_step.input_hash,
            )
        return await self._runs.transition_run(
            session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RUNNING,
            reason_code="reconciled_not_sent_new_attempt",
        )

    @staticmethod
    async def _assert_execution_authority(
        session: AsyncSession,
        run: AgentRunRecord,
        execution: AgentExternalExecutionRecord,
    ) -> tuple[AgentStepRecord, AgentBudgetReservationRecord]:
        step = await session.get(AgentStepRecord, execution.step_id)
        authorization = await session.get(
            ModelTransferAuthorizationRecord, execution.authorization_id
        )
        reservation = await session.get(
            AgentBudgetReservationRecord, execution.reservation_id
        )
        budget = (
            await session.get(AgentRootBudgetRecord, reservation.budget_id)
            if reservation is not None
            else None
        )
        now = datetime.now(UTC)
        if (
            run.research_context_id is None
            or execution.research_context_id != run.research_context_id
            or step is None
            or step.run_id != run.run_id
            or step.attempt != execution.attempt
            or step.input_hash != execution.input_hash
            or authorization is None
            or authorization.research_context_id != run.research_context_id
            or authorization.status != AuthorizationStatus.ACTIVE
            or authorization.revoked_at is not None
            or _as_utc(authorization.expires_at) <= now
            or reservation is None
            or reservation.child_run_id != run.run_id
            or reservation.step_id != step.step_id
            or reservation.attempt != step.attempt
            or reservation.request_fingerprint != execution.request_fingerprint
            or budget is None
            or budget.root_run_id != run.root_run_id
        ):
            raise RecoveryRequiredError("external execution authority chain is inconsistent")
        return step, reservation

    async def _has_exact_formal_output(
        self,
        session: AsyncSession,
        run: AgentRunRecord,
        step: AgentStepRecord,
        execution: AgentExternalExecutionRecord,
        reservation: AgentBudgetReservationRecord,
    ) -> bool:
        if (
            execution.state != "succeeded"
            or not _is_sha256(execution.result_payload_hash)
            or StepStatus(step.status) != StepStatus.COMPLETED
            or reservation.status != "settled"
            or not execution.idempotency_record_id
            or not execution.formal_artifact_id
        ):
            return False
        idem = await session.get(
            AgentIdempotencyRecord, execution.idempotency_record_id
        )
        if (
            idem is None
            or idem.research_context_id != run.research_context_id
            or idem.action != "formalize_model_result"
            or idem.request_hash != execution.request_fingerprint
            or idem.resource_type != "artifact"
            or idem.resource_id != execution.formal_artifact_id
        ):
            return False
        for raw in step.output_refs_json or []:
            if not isinstance(raw, dict) or raw.get("artifact_id") != execution.formal_artifact_id:
                continue
            try:
                ref = ArtifactRef.model_validate(raw)
                if (
                    ref.version_key != idem.resource_version
                    or ref.artifact_type != execution.expected_artifact_type
                    or ref.artifact_key != execution.expected_artifact_key
                    or ref.validity_status != ArtifactValidityStatus.VALID
                ):
                    return False
                await self._artifacts.resolve(
                    session, ref, research_context_id=run.research_context_id
                )
                return True
            except (ValueError, KeyError):
                return False
        return False
