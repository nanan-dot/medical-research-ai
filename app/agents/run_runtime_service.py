"""结构化 Run、Step、Event 生命周期。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_model import AgentArtifactRecord
from app.agents.artifact_service import ArtifactService
from app.agents.contracts import AgentEventPayload, ArtifactRef
from app.agents.enums import (
    PUBLIC_EVENT_TYPES,
    TERMINAL_RUN_STATUSES,
    RunStatus,
    StepStatus,
)
from app.agents.errors import InvalidStateTransitionError, RevisionConflictError
from app.agents.hash_schema import content_hash
from app.agents.model import AgentRunRecord
from app.agents.outbox_service import OutboxService
from app.agents.runtime_model import (
    AgentEventRecord,
    AgentStepRecord,
    AgentTaskRequestRecord,
)

RUN_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.AWAITING_USER_INPUT,
            RunStatus.AWAITING_CONFIRMATION,
            RunStatus.RECOVERY_REQUIRED,
            RunStatus.COMPLETED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.REJECTED,
            RunStatus.CANCELLED,
            RunStatus.CANCELLED_AFTER_COMMIT,
        }
    ),
    RunStatus.AWAITING_USER_INPUT: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.AWAITING_CONFIRMATION: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.REJECTED,
            RunStatus.CANCELLED,
            RunStatus.COMPLETED,
        }
    ),
    RunStatus.RECOVERY_REQUIRED: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.COMPLETED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.REJECTED,
            RunStatus.CANCELLED,
        }
    ),
}

STEP_TRANSITIONS: dict[StepStatus, frozenset[StepStatus]] = {
    StepStatus.CREATED: frozenset(
        {StepStatus.RUNNING, StepStatus.CANCELLED, StepStatus.SKIPPED}
    ),
    StepStatus.RUNNING: frozenset(
        {
            StepStatus.AWAITING_USER_INPUT,
            StepStatus.AWAITING_CONFIRMATION,
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
        }
    ),
    StepStatus.AWAITING_USER_INPUT: frozenset(
        {StepStatus.RUNNING, StepStatus.CANCELLED}
    ),
    StepStatus.AWAITING_CONFIRMATION: frozenset(
        {StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.CANCELLED}
    ),
}

ALLOWED_EVENT_DETAILS: dict[str, frozenset[str]] = {
    "state_transition": frozenset({"from_status", "status", "reason_code", "revision"}),
    "artifact_registered": frozenset({"artifact_type", "version_key", "count"}),
    "confirmation": frozenset({"action", "status", "role", "revision"}),
    "authorization": frozenset({"purpose", "provider", "model", "status", "revision"}),
    "budget": frozenset({"status", "reason_code", "reservation_id", "counts"}),
    "error": frozenset({"error_code", "stage", "retryable"}),
    "recovery": frozenset({"status", "reason_code", "attempt"}),
    "invalidation": frozenset({"status", "reason_code", "artifact_type"}),
    "model_call": frozenset(
        {
            "authorization_id",
            "reservation_id",
            "provider",
            "model",
            "purpose",
            "profile_id",
            "prompt_version",
            "schema_version",
            "status",
            "input_tokens",
            "output_tokens",
            "total_http",
        }
    ),
}


class RunRuntimeService:
    def __init__(
        self,
        outbox: OutboxService | None = None,
        artifacts: ArtifactService | None = None,
    ) -> None:
        self._outbox = outbox or OutboxService()
        self._artifacts = artifacts or ArtifactService()

    async def create_run(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        task_request_id: str,
        agent_type: str,
        run_mode: str,
        parent_run_id: str | None = None,
    ) -> AgentRunRecord:
        task = await session.get(AgentTaskRequestRecord, task_request_id)
        if task is not None and (
            task.research_context_id != research_context_id
            or task.requested_agent != agent_type
        ):
            raise ValueError("Run identity must match its TaskRequest")
        parent = None
        if parent_run_id is not None:
            parent = await session.get(AgentRunRecord, parent_run_id)
            if parent is None or parent.research_context_id != research_context_id:
                raise ValueError("parent Run is outside the research context")
        now = datetime.now(UTC)
        run_id = str(uuid4())
        run = AgentRunRecord(
            run_id=run_id,
            workflow_status=RunStatus.CREATED,
            state_json={},
            events_json=[],
            retrieval_trace_json=None,
            research_context_id=research_context_id,
            task_request_id=task_request_id,
            root_run_id=parent.root_run_id if parent is not None else run_id,
            parent_run_id=parent_run_id,
            agent_type=agent_type,
            run_mode=run_mode,
            phase=None,
            reason_code=None,
            revision=1,
            cancel_requested_at=None,
            started_at=None,
            completed_at=None,
            is_legacy=False,
            created_at=now,
            updated_at=now,
        )
        session.add(run)
        self._outbox.add(
            session,
            aggregate_type="run",
            aggregate_id=run.run_id,
            event_type="run.created",
            payload={
                "run_id": run.run_id,
                "research_context_id": research_context_id,
                "agent_type": agent_type,
                "run_mode": run_mode,
                "revision": 1,
            },
        )
        await session.flush()
        return run

    async def transition_run(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        expected_revision: int,
        next_status: RunStatus,
        reason_code: str | None = None,
        cancel_requested_at: datetime | None = None,
    ) -> AgentRunRecord:
        run = await session.get(AgentRunRecord, run_id)
        if run is None:
            raise KeyError(run_id)
        current = RunStatus(run.workflow_status)
        if current in TERMINAL_RUN_STATUSES or next_status not in RUN_TRANSITIONS.get(
            current, frozenset()
        ):
            raise InvalidStateTransitionError(f"{current} -> {next_status}")
        now = datetime.now(UTC)
        values: dict[str, object] = {
            "workflow_status": next_status,
            "reason_code": reason_code,
            "revision": AgentRunRecord.revision + 1,
            "updated_at": now,
        }
        if next_status == RunStatus.RUNNING and run.started_at is None:
            values["started_at"] = now
        if next_status in TERMINAL_RUN_STATUSES:
            values["completed_at"] = now
        if cancel_requested_at is not None:
            values["cancel_requested_at"] = cancel_requested_at
        result = await session.execute(
            update(AgentRunRecord)
            .where(
                AgentRunRecord.run_id == run_id,
                AgentRunRecord.revision == expected_revision,
            )
            .values(**values)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        await session.flush()
        await session.refresh(run)
        self._outbox.add(
            session,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="run.status_changed",
            payload={
                "run_id": run_id,
                "status": next_status,
                "reason_code": reason_code,
                "revision": run.revision,
            },
        )
        return run

    async def create_step(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        step_kind: str,
        attempt: int,
        input_hash: str | None,
    ) -> AgentStepRecord:
        step = AgentStepRecord(
            step_id=str(uuid4()),
            run_id=run_id,
            step_kind=step_kind,
            status=StepStatus.CREATED,
            attempt=attempt,
            input_hash=input_hash,
            output_refs_json=[],
            expected_revision=None,
            started_at=None,
            ended_at=None,
            error_code=None,
            revision=1,
        )
        session.add(step)
        self._outbox.add(
            session,
            aggregate_type="step",
            aggregate_id=step.step_id,
            event_type="step.status_changed",
            payload={
                "step_id": step.step_id,
                "run_id": run_id,
                "status": StepStatus.CREATED,
                "revision": 1,
            },
        )
        await session.flush()
        return step

    async def transition_step(
        self,
        session: AsyncSession,
        *,
        step_id: str,
        expected_revision: int,
        next_status: StepStatus,
        error_code: str | None = None,
        output_refs: tuple[ArtifactRef, ...] | None = None,
    ) -> AgentStepRecord:
        step = await session.get(AgentStepRecord, step_id)
        if step is None:
            raise KeyError(step_id)
        current = StepStatus(step.status)
        if next_status not in STEP_TRANSITIONS.get(current, frozenset()):
            raise InvalidStateTransitionError(f"{current} -> {next_status}")
        now = datetime.now(UTC)
        values: dict[str, object] = {
            "status": next_status,
            "error_code": error_code,
            "revision": AgentStepRecord.revision + 1,
        }
        if next_status == StepStatus.RUNNING and step.started_at is None:
            values["started_at"] = now
        if next_status in {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
            StepStatus.SKIPPED,
        }:
            values["ended_at"] = now
        if output_refs is not None:
            if next_status != StepStatus.COMPLETED:
                raise ValueError(
                    "output refs can only be committed by a completed step"
                )
            run = await session.get(AgentRunRecord, step.run_id)
            if run is None or run.research_context_id is None:
                raise KeyError(step.run_id)
            for ref in output_refs:
                await self._artifacts.resolve(
                    session, ref, research_context_id=run.research_context_id
                )
            values["output_refs_json"] = [
                ref.model_dump(mode="json") for ref in output_refs
            ]
        result = await session.execute(
            update(AgentStepRecord)
            .where(
                AgentStepRecord.step_id == step_id,
                AgentStepRecord.revision == expected_revision,
            )
            .values(**values)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        await session.flush()
        await session.refresh(step)
        self._outbox.add(
            session,
            aggregate_type="step",
            aggregate_id=step_id,
            event_type="step.status_changed",
            payload={
                "step_id": step_id,
                "run_id": step.run_id,
                "status": next_status,
                "error_code": error_code,
                "revision": step.revision,
            },
        )
        return step

    async def append_event(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        event_type: str,
        payload: AgentEventPayload,
        step_id: str | None = None,
    ) -> AgentEventRecord:
        if event_type not in PUBLIC_EVENT_TYPES:
            raise ValueError("event type is not part of the frozen public contract")
        allowed_keys = ALLOWED_EVENT_DETAILS.get(payload.detail_kind)
        if allowed_keys is None:
            raise ValueError("event detail kind is not allowed")
        if not payload.detail.keys() <= allowed_keys:
            raise ValueError("event detail contains non-whitelisted fields")
        seq = (
            await session.scalar(
                select(func.max(AgentEventRecord.seq)).where(
                    AgentEventRecord.run_id == run_id
                )
            )
        ) or 0
        hash_payload = {
            "detail_kind": payload.detail_kind,
            "detail": payload.detail,
            "artifact_refs": [
                ref.model_dump(mode="json") for ref in payload.artifact_refs
            ],
        }
        event = AgentEventRecord(
            event_id=str(uuid4()),
            run_id=run_id,
            seq=seq + 1,
            step_id=step_id,
            event_type=event_type,
            detail_kind=payload.detail_kind,
            detail_json=payload.detail,
            artifact_refs_json=[
                ref.model_dump(mode="json") for ref in payload.artifact_refs
            ],
            payload_hash=content_hash(hash_payload),
            occurred_at=datetime.now(UTC),
        )
        session.add(event)
        self._outbox.add(
            session,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type=event_type,
            event_id=event.event_id,
            payload={
                "event_id": event.event_id,
                "run_id": run_id,
                "step_id": step_id,
                "seq": event.seq,
                "payload_hash": event.payload_hash,
            },
        )
        await session.flush()
        return event

    async def cancel_run(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        expected_revision: int,
    ) -> tuple[str, AgentRunRecord]:
        run = await session.get(AgentRunRecord, run_id)
        if run is None:
            raise KeyError(run_id)
        current = RunStatus(run.workflow_status)
        if current in TERMINAL_RUN_STATUSES:
            return "too_late", run
        has_committed_output = await self._has_committed_output(session, run)
        next_status = (
            RunStatus.CANCELLED_AFTER_COMMIT
            if run.run_mode == "composite_workflow" and has_committed_output
            else RunStatus.CANCELLED
        )
        changed = await self.transition_run(
            session,
            run_id=run_id,
            expected_revision=expected_revision,
            next_status=next_status,
            reason_code="cancel_requested",
            cancel_requested_at=datetime.now(UTC),
        )
        return "cancelled", changed

    @staticmethod
    async def _has_committed_output(session: AsyncSession, run: AgentRunRecord) -> bool:
        steps = await session.scalars(
            select(AgentStepRecord).where(AgentStepRecord.run_id == run.run_id)
        )
        for step in steps:
            for raw_ref in step.output_refs_json or []:
                if not isinstance(raw_ref, dict):
                    continue
                artifact_id = raw_ref.get("artifact_id")
                if not isinstance(artifact_id, str):
                    continue
                artifact = await session.get(AgentArtifactRecord, artifact_id)
                if (
                    artifact is not None
                    and artifact.research_context_id == run.research_context_id
                    and raw_ref.get("version_key") == artifact.version_key
                    and raw_ref.get("content_hash") == artifact.content_hash
                ):
                    return True
        return False
