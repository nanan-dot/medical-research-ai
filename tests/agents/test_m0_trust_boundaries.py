"""Adversarial acceptance tests added after the independent M0 audit."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

import app.core.models  # noqa: F401
from app.agents.artifact_registry import policy_for
from app.agents.artifact_service import ArtifactService
from app.agents.authorization_service import AuthorizationService
from app.agents.budget_service import BudgetService
from app.agents.confirmation_model import (
    AgentRoleQualificationRecord,
    ResearchContextMembershipRecord,
)
from app.agents.confirmation_service import ConfirmationService
from app.agents.enums import ArtifactValidityStatus, RunStatus, StepStatus
from app.agents.errors import (
    AuthorizationRejectedError,
    InvalidStateTransitionError,
    PermissionDeniedError,
    RecoveryRequiredError,
    RevisionConflictError,
)
from app.agents.external_execution_service import ExternalExecutionService
from app.agents.hash_schema import content_hash
from app.agents.idempotency_service import IdempotencyService
from app.agents.legacy_adapter import LegacyRunAdapter
from app.agents.m0_api_schemas import (
    AuthorizationCreateRequest,
    ConfirmationDecisionRequest,
    RuntimeRecoveryRequest,
)
from app.agents.model import AgentRunRecord
from app.agents.model_gateway import (
    AuthorizedModelGateway,
    ModelPayloadEnvelope,
    ModelUsage,
    ProviderResult,
)
from app.agents.permission_service import PermissionService
from app.agents.recovery_service import RecoveryService
from app.agents.repository import AgentRunRepository
from app.agents.run_runtime_service import RunRuntimeService
from app.agents.run_service import AgentRunService
from app.agents.runtime_model import (
    AgentExternalExecutionRecord,
    AgentTaskRequestRecord,
)
from app.agents.transaction import ImmediateUnitOfWork
from app.core.database import Base


class CancellationOutput(BaseModel):
    value: str


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncEngine:
    value = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'trust.db'}")
    async with value.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield value
    await value.dispose()


async def seed_identity(session: AsyncSession, context: str = "ctx") -> None:
    session.add(
        ResearchContextMembershipRecord(
            membership_id=f"membership-{context}",
            research_context_id=context,
            actor_scope="local-owner",
            membership_role="owner",
            status="active",
            created_at=datetime.now(UTC),
            revoked_at=None,
        )
    )


async def create_running_run(
    session: AsyncSession, *, context: str = "ctx", agent: str = "A2"
) -> tuple[AgentRunRecord, object]:
    task = AgentTaskRequestRecord(
        task_request_id=f"task-{context}-{agent}",
        research_context_id=context,
        requested_agent=agent,
        intent="acceptance",
        input_artifact_refs_json=[],
        authorization_refs_json=[],
        request_hash="a" * 64,
        created_by="local-owner",
        created_at=datetime.now(UTC),
    )
    session.add(task)
    await session.flush()
    runs = RunRuntimeService()
    run = await runs.create_run(
        session,
        research_context_id=context,
        task_request_id=task.task_request_id,
        agent_type=agent,
        run_mode="standalone_confirmation",
    )
    run = await runs.transition_run(
        session,
        run_id=run.run_id,
        expected_revision=1,
        next_status=RunStatus.RUNNING,
    )
    step = await runs.create_step(
        session, run_id=run.run_id, step_kind="model", attempt=1, input_hash=None
    )
    step = await runs.transition_step(
        session,
        step_id=step.step_id,
        expected_revision=1,
        next_status=StepStatus.RUNNING,
    )
    return run, step


def test_recovery_and_confirmation_apis_reject_client_asserted_authority() -> None:
    with pytest.raises(ValidationError):
        RuntimeRecoveryRequest.model_validate(
            {
                "expected_revision": 1,
                "external_request_state": "sent_with_result",
                "formal_result_exists": True,
            }
        )


def test_production_agent_runtime_never_calls_create_all() -> None:
    agent_root = Path(__file__).parents[2] / "app" / "agents"
    offenders = [
        path
        for path in agent_root.glob("*.py")
        if "create_all" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_legacy_service_rejects_writes_without_explicit_test_capability(
    tmp_path: Path,
) -> None:
    service = AgentRunService(
        repository=AgentRunRepository(
            create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
        )
    )
    with pytest.raises(RuntimeError, match="legacy_agent_run_writes_retired"):
        service.start({"user_query": "blocked"})


@pytest.mark.asyncio
async def test_legacy_json_is_read_only_and_structured_run_does_not_dual_write(
    engine: AsyncEngine,
) -> None:
    legacy = AgentRunRecord(
        run_id="legacy",
        workflow_status="completed",
        state_json={"answer": "historical"},
        events_json=[{"kind": "historical"}],
        retrieval_trace_json={"query": "historical"},
        is_legacy=True,
        revision=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    snapshot = LegacyRunAdapter().read(legacy)
    assert snapshot.state == {"answer": "historical"}
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, _ = await create_running_run(uow.session, context="no-dual-write")
        await uow.commit()
    assert run.state_json == {}
    assert run.events_json == []
    assert run.retrieval_trace_json is None
    with pytest.raises(ValidationError):
        ConfirmationDecisionRequest.model_validate(
            {
                "expected_revision": 1,
                "decision": "approve",
                "authorized_role": "medical_reviewer",
            }
        )


@pytest.mark.asyncio
async def test_recovery_uses_server_execution_ledger(engine: AsyncEngine) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session)
        run = await RunRuntimeService().transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RECOVERY_REQUIRED,
        )
        execution = await ExternalExecutionService().prepare(
            uow.session,
            run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            request_fingerprint="b" * 64,
            authorization_id="authorization",
            reservation_id="reservation",
        )
        await ExternalExecutionService().transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=1,
            expected_state="prepared",
            next_state="sent",
        )
        with pytest.raises(RecoveryRequiredError):
            await RecoveryService().recover(
                uow.session, run_id=run.run_id, expected_revision=run.revision
            )


@pytest.mark.asyncio
async def test_recovery_selects_latest_execution_by_monotonic_sequence(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, first_step = await create_running_run(uow.session)
        service = ExternalExecutionService()
        first = await service.prepare(
            uow.session,
            run_id=run.run_id,
            step_id=first_step.step_id,
            attempt=first_step.attempt,
            request_fingerprint="7" * 64,
            authorization_id="authorization-1",
            reservation_id="reservation-1",
        )
        second_step = await RunRuntimeService().create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="model_retry",
            attempt=2,
            input_hash=None,
        )
        second = await service.prepare(
            uow.session,
            run_id=run.run_id,
            step_id=second_step.step_id,
            attempt=second_step.attempt,
            request_fingerprint="8" * 64,
            authorization_id="authorization-2",
            reservation_id="reservation-2",
        )
        first.created_at = datetime.now(UTC) + timedelta(days=1)
        second.created_at = datetime.now(UTC) - timedelta(days=1)
        assert (first.execution_seq, second.execution_seq) == (1, 2)
        run = await RunRuntimeService().transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RECOVERY_REQUIRED,
        )

        async def assert_selected(
            _session: AsyncSession,
            _run: AgentRunRecord,
            execution: AgentExternalExecutionRecord,
        ) -> None:
            assert execution.execution_id == second.execution_id
            raise RecoveryRequiredError("latest sequence selected")

        monkeypatch.setattr(
            RecoveryService,
            "_assert_execution_authority",
            staticmethod(assert_selected),
        )
        with pytest.raises(RecoveryRequiredError, match="latest sequence selected"):
            await RecoveryService().recover(
                uow.session, run_id=run.run_id, expected_revision=run.revision
            )


@pytest.mark.parametrize("next_state", ["succeeded", "outcome_unknown"])
@pytest.mark.asyncio
async def test_external_execution_rejects_skipping_sent(
    engine: AsyncEngine, next_state: str
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session)
        execution = await ExternalExecutionService().prepare(
            uow.session,
            run_id=run.run_id,
            step_id=step.step_id,
            attempt=step.attempt,
            request_fingerprint="1" * 64,
            authorization_id="authorization",
            reservation_id="reservation",
        )
        with pytest.raises(InvalidStateTransitionError):
            await ExternalExecutionService().transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="prepared",
                next_state=next_state,
                result_payload_hash="a" * 64 if next_state == "succeeded" else None,
            )


@pytest.mark.parametrize(
    "invalid_hash", [None, "a" * 63, "g" * 64, "A" * 64]
)
@pytest.mark.asyncio
async def test_external_execution_succeeded_requires_result_hash(
    engine: AsyncEngine, invalid_hash: str | None
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session)
        service = ExternalExecutionService()
        execution = await service.prepare(
            uow.session,
            run_id=run.run_id,
            step_id=step.step_id,
            attempt=step.attempt,
            request_fingerprint="2" * 64,
            authorization_id="authorization",
            reservation_id="reservation",
        )
        execution = await service.transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            expected_state="prepared",
            next_state="sent",
        )
        with pytest.raises(InvalidStateTransitionError):
            await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="sent",
                next_state="succeeded",
                result_payload_hash=invalid_hash,
            )


@pytest.mark.parametrize(
    "terminal_state", ["succeeded", "failed_before_send", "outcome_unknown"]
)
@pytest.mark.asyncio
async def test_external_execution_terminal_states_cannot_transition(
    engine: AsyncEngine, terminal_state: str
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session)
        service = ExternalExecutionService()
        execution = await service.prepare(
            uow.session,
            run_id=run.run_id,
            step_id=step.step_id,
            attempt=step.attempt,
            request_fingerprint="3" * 64,
            authorization_id="authorization",
            reservation_id="reservation",
        )
        if terminal_state == "succeeded":
            execution = await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="prepared",
                next_state="sent",
            )
            execution = await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="sent",
                next_state="succeeded",
                result_payload_hash="b" * 64,
            )
        elif terminal_state == "failed_before_send":
            execution = await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="prepared",
                next_state="failed_before_send",
            )
        else:
            execution = await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="prepared",
                next_state="sent",
            )
            execution = await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state="sent",
                next_state="outcome_unknown",
            )
        with pytest.raises(InvalidStateTransitionError):
            await service.transition(
                uow.session,
                execution_id=execution.execution_id,
                expected_revision=execution.revision,
                expected_state=terminal_state,
                next_state="sent",
            )


@pytest.mark.asyncio
async def test_latest_unknown_execution_cannot_reuse_old_step_artifact(
    engine: AsyncEngine,
) -> None:
    payload = {"claim": "candidate"}
    fingerprint = "c" * 64
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session)
        run, old_step = await create_running_run(uow.session)
        old_artifact = await ArtifactService().register(
            uow.session,
            research_context_id="ctx",
            artifact_type="test",
            artifact_key="old",
            version_key="1",
            schema_version="1",
            payload={"value": "old"},
            created_by="local-owner",
        )
        await RunRuntimeService().transition_step(
            uow.session,
            step_id=old_step.step_id,
            expected_revision=old_step.revision,
            next_status=StepStatus.COMPLETED,
            output_refs=(old_artifact,),
        )
        latest_step = await RunRuntimeService().create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="model",
            attempt=2,
            input_hash=content_hash(payload),
        )
        latest_step = await RunRuntimeService().transition_step(
            uow.session,
            step_id=latest_step.step_id,
            expected_revision=latest_step.revision,
            next_status=StepStatus.RUNNING,
        )
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash=content_hash(payload),
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id="recovery-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 10,
                "output_tokens": 10,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 10,
            },
        )
        reservation = await BudgetService().reserve(
            uow.session,
            budget_id="recovery-budget",
            child_run_id=run.run_id,
            step_id=latest_step.step_id,
            attempt=2,
            provider="provider",
            requested={
                "model_attempts": 1,
                "input_tokens": 10,
                "output_tokens": 10,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 10,
            },
            request_fingerprint=fingerprint,
        )
        execution = await ExternalExecutionService().prepare(
            uow.session,
            run_id=run.run_id,
            step_id=latest_step.step_id,
            attempt=2,
            request_fingerprint=fingerprint,
            authorization_id=authorization.authorization_id,
            reservation_id=reservation.reservation_id,
            expected_artifact_type="test",
            expected_artifact_key="new",
        )
        execution = await ExternalExecutionService().transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            expected_state="prepared",
            next_state="sent",
        )
        await ExternalExecutionService().transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            expected_state="sent",
            next_state="outcome_unknown",
        )
        run = await RunRuntimeService().transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RECOVERY_REQUIRED,
        )
        with pytest.raises(RecoveryRequiredError):
            await RecoveryService().recover(
                uow.session, run_id=run.run_id, expected_revision=run.revision
            )


def test_authorization_vocabulary_is_closed() -> None:
    with pytest.raises(ValidationError):
        AuthorizationCreateRequest.model_validate(
            {
                "research_context_id": "ctx",
                "provider": "provider",
                "model": "model",
                "purpose": "extract",
                "content_granularity": "claim",
                "data_categories": ["paper_text"],
                "payload_refs": [],
                "payload_hash": "a" * 64,
                "payload_shape": "single_item",
                "content_transform": "raw",
                "allow_cloud_transfer": True,
            }
        )


@pytest.mark.asyncio
async def test_recovery_completes_only_exact_bound_formal_artifact(
    engine: AsyncEngine,
) -> None:
    payload = {"claim": "candidate"}
    fingerprint = "e" * 64
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session)
        run, step = await create_running_run(uow.session)
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash=content_hash(payload),
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id="exact-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 10,
                "output_tokens": 10,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 10,
            },
        )
        reservation = await BudgetService().reserve(
            uow.session,
            budget_id="exact-budget",
            child_run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            provider="provider",
            requested={
                "model_attempts": 1,
                "input_tokens": 10,
                "output_tokens": 10,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 10,
            },
            request_fingerprint=fingerprint,
        )
        execution = await ExternalExecutionService().prepare(
            uow.session,
            run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            request_fingerprint=fingerprint,
            authorization_id=authorization.authorization_id,
            reservation_id=reservation.reservation_id,
            expected_artifact_type="test",
            expected_artifact_key="exact",
        )
        execution = await ExternalExecutionService().transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            expected_state="prepared",
            next_state="sent",
        )
        execution = await ExternalExecutionService().transition(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            expected_state="sent",
            next_state="succeeded",
            result_payload_hash=content_hash({"value": "exact"}),
        )
        await BudgetService().settle(
            uow.session,
            reservation_id=reservation.reservation_id,
            actual={
                "model_attempts": 1,
                "input_tokens": 1,
                "output_tokens": 1,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 1,
            },
        )
        artifact = await ArtifactService().register(
            uow.session,
            research_context_id="ctx",
            artifact_type="test",
            artifact_key="exact",
            version_key="1",
            schema_version="1",
            payload={"value": "exact"},
            created_by="local-owner",
        )
        step = await RunRuntimeService().transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=step.revision,
            next_status=StepStatus.COMPLETED,
            output_refs=(artifact,),
        )
        idem = IdempotencyService().add(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            action="formalize_model_result",
            key="exact-result",
            request_hash=fingerprint,
            resource_type="artifact",
            resource_id=artifact.artifact_id,
            resource_version=artifact.version_key,
        )
        await uow.session.flush()
        await ExternalExecutionService().bind_formal_result(
            uow.session,
            execution_id=execution.execution_id,
            expected_revision=execution.revision,
            idempotency_record_id=idem.idempotency_id,
            artifact_ref=artifact,
        )
        run = await RunRuntimeService().transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RECOVERY_REQUIRED,
        )
        recovered = await RecoveryService().recover(
            uow.session, run_id=run.run_id, expected_revision=run.revision
        )
        assert recovered.workflow_status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_authorization_checks_every_payload_dimension(
    engine: AsyncEngine,
) -> None:
    payload = {"claim": "candidate"}
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session)
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash=content_hash(payload),
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        for changed in (
            {"content_granularity": "document"},
            {"data_categories": ("patient_data",)},
            {"payload_shape": "multi_item_bundle"},
        ):
            arguments = {
                "authorization_id": authorization.authorization_id,
                "research_context_id": "ctx",
                "actor_scope": "local-owner",
                "provider": "provider",
                "model": "model",
                "purpose": "extract",
                "content_granularity": "section",
                "data_categories": ("document_text",),
                "payload_refs": (),
                "payload_hash": content_hash(payload),
                "payload_shape": "single_item",
                "content_transform": "raw",
                "is_cloud": True,
            }
            arguments.update(changed)
            with pytest.raises(AuthorizationRejectedError):
                await AuthorizationService().assert_allowed(uow.session, **arguments)


@pytest.mark.asyncio
async def test_confirmation_consumes_authoritative_revision_and_role(
    engine: AsyncEngine,
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session)
        run, _ = await create_running_run(uow.session)
        target = await ArtifactService().register(
            uow.session,
            research_context_id="ctx",
            artifact_type="draft",
            artifact_key="draft",
            version_key="1",
            schema_version="1",
            payload={"claim": "candidate"},
            created_by="local-owner",
        )
        confirmation = await ConfirmationService().request(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(target,),
            expected_revisions={f"run:{run.run_id}": run.revision},
        )
        await RunRuntimeService().transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.AWAITING_CONFIRMATION,
        )
        with pytest.raises(RevisionConflictError):
            await ConfirmationService().consume(
                uow.session,
                confirmation_id=confirmation.confirmation_id,
                expected_revision=1,
                actor_scope="local-owner",
                decision="approve",
            )


@pytest.mark.asyncio
async def test_expired_professional_qualification_is_rejected(
    engine: AsyncEngine,
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session)
        uow.session.add(
            AgentRoleQualificationRecord(
                qualification_id="expired-medical",
                actor_scope="local-owner",
                authorized_role="medical_reviewer",
                source_kind="credential",
                source_ref="expired",
                valid_from=datetime.now(UTC) - timedelta(days=10),
                valid_until=datetime.now(UTC) - timedelta(days=1),
                status="active",
                revision=1,
            )
        )
        target = await ArtifactService().register(
            uow.session,
            research_context_id="ctx",
            artifact_type="draft",
            artifact_key="medical",
            version_key="1",
            schema_version="1",
            payload={"claim": "medical"},
            created_by="local-owner",
        )
        confirmation = await ConfirmationService().request(
            uow.session,
            research_context_id="ctx",
            actor_scope="local-owner",
            action="approve_medical_review",
            target_refs=(target,),
            expected_revisions={},
        )
        with pytest.raises(PermissionDeniedError):
            await ConfirmationService().consume(
                uow.session,
                confirmation_id=confirmation.confirmation_id,
                expected_revision=1,
                actor_scope="local-owner",
                decision="approve",
            )


@pytest.mark.asyncio
async def test_revoked_professional_qualification_is_rejected(
    engine: AsyncEngine,
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        uow.session.add(
            AgentRoleQualificationRecord(
                qualification_id="revoked-medical",
                actor_scope="local-owner",
                authorized_role="medical_reviewer",
                source_kind="credential",
                source_ref="revoked",
                valid_from=datetime.now(UTC) - timedelta(days=10),
                valid_until=datetime.now(UTC) + timedelta(days=10),
                status="revoked",
                revision=2,
            )
        )
        await uow.session.flush()
        with pytest.raises(PermissionDeniedError):
            await PermissionService().require_qualification(
                uow.session, "local-owner", "medical_reviewer"
            )


@pytest.mark.asyncio
async def test_budget_rejects_cross_root_and_total_mismatch(
    engine: AsyncEngine,
) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session, context="budget")
        BudgetService().create_budget(
            uow.session,
            budget_id="wrong-root-budget",
            root_run_id="different-root",
            limits={"model_attempts": 1, "total_http_attempts": 0},
        )
        with pytest.raises(ValueError, match="share one root"):
            await BudgetService().reserve(
                uow.session,
                budget_id="wrong-root-budget",
                child_run_id=run.run_id,
                step_id=step.step_id,
                attempt=1,
                provider="provider",
                requested={"model_attempts": 1},
                request_fingerprint="c" * 64,
            )
        with pytest.raises(ValueError, match="must equal"):
            BudgetService().create_budget(
                uow.session,
                budget_id="bad-total",
                root_run_id=run.run_id,
                limits={"model_http_attempts": 1, "total_http_attempts": 0},
            )


@pytest.mark.asyncio
async def test_budget_reservation_replay_is_idempotent(engine: AsyncEngine) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        run, step = await create_running_run(uow.session, context="budget-replay")
        service = BudgetService()
        service.create_budget(
            uow.session,
            budget_id="replay-budget",
            root_run_id=run.run_id,
            limits={"model_attempts": 1, "total_http_attempts": 0},
        )
        first = await service.reserve(
            uow.session,
            budget_id="replay-budget",
            child_run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            provider="provider",
            requested={"model_attempts": 1},
            request_fingerprint="e" * 64,
        )
        replay = await service.reserve(
            uow.session,
            budget_id="replay-budget",
            child_run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            provider="provider",
            requested={"model_attempts": 1},
            request_fingerprint="e" * 64,
        )
        assert replay.reservation_id == first.reservation_id


@pytest.mark.asyncio
async def test_artifact_registry_rejects_unknown_and_maps_exactly(
    engine: AsyncEngine,
) -> None:
    with pytest.raises(ValueError, match="unknown artifact_type"):
        policy_for("synthesis-looking-unknown")
    assert (
        policy_for("evidence_matrix_snapshot").downstream_status
        == ArtifactValidityStatus.STALE
    )
    assert (
        policy_for("study_design_version").downstream_status
        == ArtifactValidityStatus.NEEDS_REVALIDATION
    )
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        with pytest.raises(ValueError, match="unknown artifact_type"):
            await ArtifactService().register(
                uow.session,
                research_context_id="ctx",
                artifact_type="unknown",
                artifact_key="key",
                version_key="1",
                schema_version="1",
                payload={"id": "key"},
                created_by="local-owner",
            )


@pytest.mark.asyncio
async def test_run_identity_must_match_task_request(engine: AsyncEngine) -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        task = AgentTaskRequestRecord(
            task_request_id="a1-task",
            research_context_id="ctx",
            requested_agent="A1",
            intent="search",
            input_artifact_refs_json=[],
            authorization_refs_json=[],
            request_hash="d" * 64,
            created_by="local-owner",
            created_at=datetime.now(UTC),
        )
        uow.session.add(task)
        await uow.session.flush()
        with pytest.raises(ValueError, match="must match"):
            await RunRuntimeService().create_run(
                uow.session,
                research_context_id="ctx",
                task_request_id=task.task_request_id,
                agent_type="A2",
                run_mode="standalone_confirmation",
            )


@pytest.mark.asyncio
async def test_cancellation_wins_before_model_send(engine: AsyncEngine) -> None:
    payload = {"claim": "candidate"}
    checkpoint_reached = asyncio.Event()
    resume_gateway = asyncio.Event()
    provider_calls = 0

    async def checkpoint() -> None:
        checkpoint_reached.set()
        await resume_gateway.wait()

    async def provider_call(_: object) -> ProviderResult:
        nonlocal provider_calls
        provider_calls += 1
        return ProviderResult({"value": "should-not-send"}, ModelUsage(1, 1))

    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await seed_identity(uow.session, "cancel")
        run, step = await create_running_run(uow.session, context="cancel")
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="cancel",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash=content_hash(payload),
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id="cancel-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 10,
                "output_tokens": 10,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 10,
            },
        )
        await uow.commit()

    gateway_task = asyncio.create_task(
        AuthorizedModelGateway[CancellationOutput](
            engine, before_send_checkpoint=checkpoint
        ).invoke(
            authorization_id=authorization.authorization_id,
            budget_id="cancel-budget",
            research_context_id="cancel",
            actor_scope="local-owner",
            child_run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            provider="provider",
            model="model",
            purpose="extract",
            profile_id="default",
            prompt_version="v1",
            schema_version="v1",
            is_cloud=True,
            envelope=ModelPayloadEnvelope(
                content=payload,
                content_granularity="section",
                data_categories=("document_text",),
                payload_refs=(),
                payload_shape="single_item",
                content_transform="raw",
            ),
            max_input_tokens=10,
            max_output_tokens=10,
            max_model_http_attempts=1,
            max_active_seconds=10,
            provider_retries_disabled=True,
            output_schema=CancellationOutput,
            provider_call=provider_call,
        )
    )
    await checkpoint_reached.wait()
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        await RunRuntimeService().cancel_run(
            uow.session, run_id=run.run_id, expected_revision=run.revision
        )
        await uow.commit()
    resume_gateway.set()
    with pytest.raises(InvalidStateTransitionError):
        await gateway_task
    async with AsyncSession(engine) as session:
        execution = await session.scalar(select(AgentExternalExecutionRecord))
        assert execution is not None and execution.state == "failed_before_send"
    assert provider_calls == 0

