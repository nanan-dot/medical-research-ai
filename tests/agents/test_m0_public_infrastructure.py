"""M0 公共基础设施的验收测试。"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.core.models  # noqa: F401 - register all metadata
from app.agents.artifact_model import AgentArtifactRecord
from app.agents.artifact_service import ArtifactService
from app.agents.authorization_service import AuthorizationService
from app.agents.budget_model import (
    AgentBudgetReservationRecord,
    AgentRootBudgetRecord,
)
from app.agents.budget_service import BudgetService
from app.agents.confirmation_model import (
    ResearchContextMembershipRecord,
    UserConfirmationRecord,
)
from app.agents.confirmation_service import ConfirmationService
from app.agents.contracts import AgentEventPayload, DependencyRef
from app.agents.enums import ArtifactValidityStatus, RunStatus, StepStatus
from app.agents.errors import (
    AuthorizationRejectedError,
    BudgetExhaustedError,
    DependencyInvalidError,
    IdempotencyKeyReusedError,
    InvalidStateTransitionError,
    PermissionDeniedError,
    RevisionConflictError,
)
from app.agents.hash_schema import CanonicalizationError, canonical_json, content_hash
from app.agents.idempotency_service import IdempotencyService
from app.agents.invalidation_service import InvalidationService
from app.agents.m0_router import router as m0_router
from app.agents.model import AgentRunRecord
from app.agents.model_gateway import (
    AuthorizedModelGateway,
    ModelPayloadEnvelope,
    ModelUsage,
    ProviderResult,
)
from app.agents.outbox_model import AgentOutboxRecord
from app.agents.outbox_publisher import OutboxPublisher
from app.agents.outbox_service import OutboxService
from app.agents.run_runtime_service import RunRuntimeService
from app.agents.runtime_model import AgentEventRecord, AgentExternalExecutionRecord
from app.agents.transaction import ImmediateUnitOfWork
from app.core.database import Base


@pytest.fixture
async def m0_engine(tmp_path: Path) -> AsyncEngine:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'm0.db'}",
        connect_args={"timeout": 10},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def add_membership(engine: AsyncEngine, context_id: str = "ctx-1") -> None:
    async with ImmediateUnitOfWork(engine) as uow:
        assert uow.session is not None
        uow.session.add(
            ResearchContextMembershipRecord(
                membership_id=f"owner-{context_id}",
                research_context_id=context_id,
                actor_scope="local-owner",
                membership_role="owner",
                status="active",
                created_at=datetime.now(UTC),
                revoked_at=None,
            )
        )
        await uow.commit()


def test_hash_schema_is_order_independent_for_object_keys() -> None:
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})
    assert len(content_hash({"unicode": "医学"})) == 64
    assert content_hash({"a": "é", "b": "1.0"}) == (
        "2221867189748eeb085fe574825a95341460e429f1d0b6730183da52adbd6db2"
    )
    assert content_hash({"n": 1}) == (
        "2bfd14f43d17fc7cea24e0917a8879b4b2f880b8baeec1b9d90fbaad655e71bd"
    )
    assert content_hash([1, 2]) != content_hash([2, 1])
    assert content_hash("é") != content_hash("e\u0301")
    assert canonical_json({"line": "a\nb", "array": [2, 1]}) == (
        b'{"array":[2,1],"line":"a\\nb"}'
    )
    assert canonical_json({"value": 1.0}) == b'{"value":1}'
    assert canonical_json({"safe_integer": 2**53 - 1})
    with pytest.raises(CanonicalizationError):
        canonical_json({"unsafe_integer": 2**53})


@pytest.mark.asyncio
async def test_outbox_publisher_retries_without_holding_network_transaction(
    m0_engine: AsyncEngine,
) -> None:
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        event = OutboxService().add(
            uow.session,
            aggregate_type="test",
            aggregate_id="aggregate",
            event_type="run.created",
            payload={"status": "ready"},
        )
        await uow.commit()
    calls = 0

    async def flaky_publish(
        event_id: str, event_type: str, payload: dict[str, object]
    ) -> None:
        nonlocal calls
        calls += 1
        assert event_id == event.event_id
        assert event_type == "run.created"
        assert payload == {"status": "ready"}
        if calls == 1:
            raise RuntimeError("temporary transport failure")

    publisher = OutboxPublisher(m0_engine, flaky_publish)
    assert await publisher.run_once() == (0, 1)
    assert await publisher.run_once() == (1, 0)
    async with AsyncSession(m0_engine) as session:
        stored = await session.get(AgentOutboxRecord, event.event_id)
        assert stored is not None
        assert stored.published_at is not None
        assert stored.attempt_count == 2
        assert stored.last_error is None


@pytest.mark.asyncio
async def test_immediate_uow_rolls_back_all_writes(m0_engine: AsyncEngine) -> None:
    with pytest.raises(RuntimeError):
        async with ImmediateUnitOfWork(m0_engine) as uow:
            assert uow.session is not None
            uow.session.add(
                ResearchContextMembershipRecord(
                    membership_id="rollback",
                    research_context_id="ctx-rollback",
                    actor_scope="local-owner",
                    membership_role="owner",
                    status="active",
                    created_at=datetime.now(UTC),
                    revoked_at=None,
                )
            )
            await uow.session.flush()
            raise RuntimeError("fault injection")
    async with m0_engine.connect() as connection:
        count = await connection.scalar(
            select(ResearchContextMembershipRecord).where(
                ResearchContextMembershipRecord.membership_id == "rollback"
            )
        )
    assert count is None


@pytest.mark.asyncio
async def test_artifact_registration_resolution_and_dependency_gate(
    m0_engine: AsyncEngine,
) -> None:
    artifacts = ArtifactService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        upstream = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="source",
            artifact_key="paper",
            version_key="v1",
            schema_version="1",
            payload={"document": "d1", "revision": "r1"},
            created_by="local-owner",
        )
        downstream = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="analysis",
            artifact_key="a1",
            version_key="v1",
            schema_version="1",
            payload={"result": "candidate"},
            created_by="local-owner",
            dependencies=(
                DependencyRef(
                    upstream_artifact_id=upstream.artifact_id,
                    upstream_version_key=upstream.version_key,
                    upstream_content_hash=upstream.content_hash,
                    dependency_kind="source",
                ),
            ),
        )
        replay = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="analysis",
            artifact_key="a1",
            version_key="v1",
            schema_version="1",
            payload={"result": "candidate"},
            created_by="local-owner",
            dependencies=(
                DependencyRef(
                    upstream_artifact_id=upstream.artifact_id,
                    upstream_version_key=upstream.version_key,
                    upstream_content_hash=upstream.content_hash,
                    dependency_kind="source",
                ),
            ),
        )
        assert replay.artifact_id == downstream.artifact_id
        await uow.commit()

    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        await InvalidationService().invalidate(
            uow.session,
            artifact_id=upstream.artifact_id,
            reason_code="source_changed",
        )
        await uow.commit()

    async with m0_engine.connect() as connection:
        async with AsyncSession(bind=connection) as session:
            with pytest.raises(DependencyInvalidError):
                await artifacts.resolve(
                    session, downstream, research_context_id="ctx-1"
                )
            with pytest.raises(PermissionDeniedError):
                await artifacts.resolve(
                    session, downstream, research_context_id="ctx-2"
                )
        downstream_status = await connection.scalar(
            select(AgentArtifactRecord.validity_status).where(
                AgentArtifactRecord.artifact_id == downstream.artifact_id
            )
        )
        outbox_count = len(
            list((await connection.execute(select(AgentOutboxRecord))).scalars())
        )
    assert downstream_status == ArtifactValidityStatus.STALE
    assert outbox_count == 4


@pytest.mark.asyncio
async def test_artifact_version_rejects_different_content(
    m0_engine: AsyncEngine,
) -> None:
    service = ArtifactService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        await service.register(
            uow.session,
            research_context_id="ctx",
            artifact_type="test",
            artifact_key="key",
            version_key="1",
            schema_version="1",
            payload={"value": 1},
            created_by="actor",
        )
        with pytest.raises(RevisionConflictError):
            await service.register(
                uow.session,
                research_context_id="ctx",
                artifact_type="test",
                artifact_key="key",
                version_key="1",
                schema_version="1",
                payload={"value": 2},
                created_by="actor",
            )


@pytest.mark.asyncio
async def test_idempotency_same_hash_replays_and_different_hash_conflicts(
    m0_engine: AsyncEngine,
) -> None:
    service = IdempotencyService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        service.add(
            uow.session,
            research_context_id="ctx",
            actor_scope="actor",
            action="create",
            key="same",
            request_hash="a" * 64,
            resource_type="artifact",
            resource_id="resource",
            resource_version="1",
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        replay = await service.find(
            uow.session,
            research_context_id="ctx",
            actor_scope="actor",
            action="create",
            key="same",
            request_hash="a" * 64,
        )
        assert replay is not None and replay.resource_id == "resource"
        with pytest.raises(IdempotencyKeyReusedError):
            await service.find(
                uow.session,
                research_context_id="ctx",
                actor_scope="actor",
                action="create",
                key="same",
                request_hash="b" * 64,
            )


@pytest.mark.asyncio
async def test_run_cas_transition_and_terminal_state(m0_engine: AsyncEngine) -> None:
    runs = RunRuntimeService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx",
            task_request_id="task",
            agent_type="A1",
            run_mode="standalone_confirmation",
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        running = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=1,
            next_status=RunStatus.RUNNING,
        )
        await runs.append_event(
            uow.session,
            run_id=run.run_id,
            event_type="run.status_changed",
            payload=AgentEventPayload(
                detail_kind="state_transition", detail={"status": "running"}
            ),
        )
        await uow.commit()
    assert running.revision == 2
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        with pytest.raises(RevisionConflictError):
            await runs.transition_run(
                uow.session,
                run_id=run.run_id,
                expected_revision=1,
                next_status=RunStatus.COMPLETED,
            )
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        completed = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=2,
            next_status=RunStatus.COMPLETED,
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        with pytest.raises(InvalidStateTransitionError):
            await runs.transition_run(
                uow.session,
                run_id=run.run_id,
                expected_revision=completed.revision,
                next_status=RunStatus.RUNNING,
            )


@pytest.mark.asyncio
async def test_composite_cancel_is_adjudicated_from_committed_step_output(
    m0_engine: AsyncEngine,
) -> None:
    runs = RunRuntimeService()
    artifacts = ArtifactService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx",
            task_request_id="task",
            agent_type="A2",
            run_mode="composite_workflow",
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=1,
            next_status=RunStatus.RUNNING,
        )
        output = await artifacts.register(
            uow.session,
            research_context_id="ctx",
            artifact_type="evidence_version",
            artifact_key="evidence",
            version_key="1",
            schema_version="1",
            payload={
                "evidence_id": "evidence",
                "evidence_version_id": "1",
                "content_hash": content_hash(
                    {"evidence_id": "evidence", "evidence_version_id": "1"}
                ),
            },
            created_by="local-owner",
        )
        step = await runs.create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="extract",
            attempt=1,
            input_hash=None,
        )
        step = await runs.transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=1,
            next_status=StepStatus.RUNNING,
        )
        await runs.transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=2,
            next_status=StepStatus.COMPLETED,
            output_refs=(output,),
        )
        _, cancelled = await runs.cancel_run(
            uow.session, run_id=run.run_id, expected_revision=run.revision
        )
        await uow.commit()
    assert cancelled.workflow_status == RunStatus.CANCELLED_AFTER_COMMIT


@pytest.mark.asyncio
async def test_confirmation_is_bound_and_single_use(m0_engine: AsyncEngine) -> None:
    await add_membership(m0_engine)
    artifacts = ArtifactService()
    confirmations = ConfirmationService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        target = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="draft",
            artifact_key="draft",
            version_key="1",
            schema_version="1",
            payload={"claim": "candidate"},
            created_by="local-owner",
        )
        confirmation = await confirmations.request(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(target,),
            expected_revisions={},
        )
        duplicate = await confirmations.request(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(target,),
            expected_revisions={},
        )
        assert duplicate.confirmation_id == confirmation.confirmation_id
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        first = await confirmations.consume(
            uow.session,
            confirmation_id=confirmation.confirmation_id,
            expected_revision=1,
            actor_scope="local-owner",
            decision="approve",
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        replay = await confirmations.consume(
            uow.session,
            confirmation_id=confirmation.confirmation_id,
            expected_revision=1,
            actor_scope="local-owner",
            decision="approve",
        )
        assert replay.decision_id == first.decision_id


@pytest.mark.asyncio
async def test_confirmation_rechecks_artifact_dependency_at_consumption(
    m0_engine: AsyncEngine,
) -> None:
    await add_membership(m0_engine)
    artifacts = ArtifactService()
    confirmations = ConfirmationService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        target = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="draft",
            artifact_key="draft-invalidated",
            version_key="1",
            schema_version="1",
            payload={"claim": "candidate"},
            created_by="local-owner",
        )
        confirmation = await confirmations.request(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(target,),
            expected_revisions={},
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        await InvalidationService().invalidate(
            uow.session,
            artifact_id=target.artifact_id,
            reason_code="upstream_changed",
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        with pytest.raises(RevisionConflictError):
            await confirmations.consume(
                uow.session,
                confirmation_id=confirmation.confirmation_id,
                expected_revision=1,
                actor_scope="local-owner",
                decision="approve",
            )
        superseded = await uow.session.get(
            UserConfirmationRecord, confirmation.confirmation_id
        )
        assert superseded is not None
        assert superseded.status == "superseded"


@pytest.mark.asyncio
async def test_supersede_invalidates_full_dependency_confirmation_closure(
    m0_engine: AsyncEngine,
) -> None:
    await add_membership(m0_engine)
    artifacts = ArtifactService()
    confirmations = ConfirmationService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        source_v1 = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="source",
            artifact_key="document",
            version_key="1",
            schema_version="1",
            payload={"document": "document", "revision": "1"},
            created_by="local-owner",
        )
        source_v2 = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="source",
            artifact_key="document",
            version_key="2",
            schema_version="1",
            payload={"document": "document", "revision": "2"},
            created_by="local-owner",
        )
        analysis = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="analysis",
            artifact_key="analysis",
            version_key="1",
            schema_version="1",
            payload={"result": "analysis"},
            created_by="local-owner",
            dependencies=(
                DependencyRef(
                    upstream_artifact_id=source_v1.artifact_id,
                    upstream_version_key=source_v1.version_key,
                    upstream_content_hash=source_v1.content_hash,
                    dependency_kind="source",
                ),
            ),
        )
        draft = await artifacts.register(
            uow.session,
            research_context_id="ctx-1",
            artifact_type="draft",
            artifact_key="draft",
            version_key="1",
            schema_version="1",
            payload={"claim": "draft"},
            created_by="local-owner",
            dependencies=(
                DependencyRef(
                    upstream_artifact_id=analysis.artifact_id,
                    upstream_version_key=analysis.version_key,
                    upstream_content_hash=analysis.content_hash,
                    dependency_kind="derived",
                ),
            ),
        )
        analysis_confirmation = await confirmations.request(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(analysis,),
            expected_revisions={},
        )
        draft_confirmation = await confirmations.request(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            action="approve_draft",
            target_refs=(draft,),
            expected_revisions={},
        )
        await uow.commit()

    # Simulate a partially invalid historical graph: traversal must continue
    # through the already-stale middle node and still close over descendants.
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        stale_analysis = await uow.session.get(
            AgentArtifactRecord, analysis.artifact_id
        )
        assert stale_analysis is not None
        stale_analysis.validity_status = ArtifactValidityStatus.STALE
        await uow.commit()

    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        await InvalidationService().supersede(
            uow.session,
            artifact_id=source_v1.artifact_id,
            replacement_artifact_id=source_v2.artifact_id,
        )
        await uow.commit()

    async with AsyncSession(m0_engine) as session:
        stored_source = await session.get(AgentArtifactRecord, source_v1.artifact_id)
        stored_analysis = await session.get(AgentArtifactRecord, analysis.artifact_id)
        stored_draft = await session.get(AgentArtifactRecord, draft.artifact_id)
        stored_analysis_confirmation = await session.get(
            UserConfirmationRecord, analysis_confirmation.confirmation_id
        )
        stored_draft_confirmation = await session.get(
            UserConfirmationRecord, draft_confirmation.confirmation_id
        )
        assert stored_source is not None
        assert stored_source.validity_status == ArtifactValidityStatus.SUPERSEDED
        assert stored_analysis is not None
        assert stored_analysis.validity_status == ArtifactValidityStatus.STALE
        assert stored_draft is not None
        assert (
            stored_draft.validity_status
            == ArtifactValidityStatus.NEEDS_REVALIDATION
        )
        assert stored_analysis_confirmation is not None
        assert stored_analysis_confirmation.status == "superseded"
        assert stored_draft_confirmation is not None
        assert stored_draft_confirmation.status == "superseded"
        confirmation_events = list(
            (
                await session.scalars(
                    select(AgentOutboxRecord).where(
                        AgentOutboxRecord.event_type
                        == "confirmation.superseded"
                    )
                )
            ).all()
        )
        assert {
            event.aggregate_id for event in confirmation_events
        } == {
            analysis_confirmation.confirmation_id,
            draft_confirmation.confirmation_id,
        }


@pytest.mark.asyncio
async def test_authorization_revocation_blocks_send(m0_engine: AsyncEngine) -> None:
    await add_membership(m0_engine)
    service = AuthorizationService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        authorization = await service.issue(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash="a" * 64,
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
            expires_in=timedelta(minutes=5),
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        await service.revoke(
            uow.session,
            authorization_id=authorization.authorization_id,
            expected_revision=1,
            actor_scope="local-owner",
        )
        await uow.commit()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        with pytest.raises(AuthorizationRejectedError):
            await service.assert_allowed(
                uow.session,
                authorization_id=authorization.authorization_id,
                research_context_id="ctx-1",
                actor_scope="local-owner",
                provider="provider",
                model="model",
                purpose="extract",
                content_granularity="section",
                data_categories=("document_text",),
                payload_refs=(),
                payload_hash="a" * 64,
                payload_shape="single_item",
                content_transform="raw",
                is_cloud=True,
            )


@pytest.mark.asyncio
async def test_concurrent_last_budget_only_one_reservation_wins(
    m0_engine: AsyncEngine,
) -> None:
    budgets = BudgetService()
    runs = RunRuntimeService()
    bindings: dict[str, tuple[str, str]] = {}
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        root = await runs.create_run(
            uow.session,
            research_context_id="ctx-budget",
            task_request_id="budget-task",
            agent_type="A1",
            run_mode="standalone_confirmation",
        )
        budgets.create_budget(
            uow.session,
            budget_id="budget",
            root_run_id=root.run_id,
            limits={
                "model_attempts": 1,
                "active_seconds": 30,
                "total_http_attempts": 0,
            },
        )
        for name in ("a", "b"):
            step = await runs.create_step(
                uow.session,
                run_id=root.run_id,
                step_kind=name,
                attempt=1,
                input_hash=None,
            )
            bindings[name] = (root.run_id, step.step_id)
        await uow.commit()

    async def reserve(name: str) -> str:
        child_run_id, step_id = bindings[name]
        try:
            async with ImmediateUnitOfWork(m0_engine) as uow:
                assert uow.session is not None
                await budgets.reserve(
                    uow.session,
                    budget_id="budget",
                    child_run_id=child_run_id,
                    step_id=step_id,
                    attempt=1,
                    provider="provider",
                    requested={"model_attempts": 1},
                    request_fingerprint=name * 64,
                )
                await uow.commit()
            return "won"
        except BudgetExhaustedError:
            return "exhausted"

    results = await asyncio.gather(reserve("a"), reserve("b"))
    assert sorted(results) == ["exhausted", "won"]


class Output(BaseModel):
    value: str


@pytest.mark.asyncio
async def test_model_gateway_checks_authorization_and_settles_usage(
    m0_engine: AsyncEngine,
) -> None:
    await add_membership(m0_engine)
    payload = {"claim": "candidate"}
    runs = RunRuntimeService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx-1",
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
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx-1",
            task_request_id="gateway-task",
            agent_type="A2",
            run_mode="standalone_confirmation",
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=1,
            next_status=RunStatus.RUNNING,
        )
        step = await runs.create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="model_extract",
            attempt=1,
            input_hash=content_hash(payload),
        )
        await runs.transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=1,
            next_status=StepStatus.RUNNING,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id="gateway-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 30,
            },
        )
        await uow.commit()

    calls = 0

    async def provider_call(value: object) -> ProviderResult:
        nonlocal calls
        calls += 1
        return ProviderResult(payload={"value": "ok"}, usage=ModelUsage(10, 4))

    result = await AuthorizedModelGateway[Output](m0_engine).invoke(
        authorization_id=authorization.authorization_id,
        budget_id="gateway-budget",
        research_context_id="ctx-1",
        actor_scope="local-owner",
        child_run_id=run.run_id,
        step_id=step.step_id,
        attempt=1,
        provider="provider",
        model="model",
        purpose="extract",
        profile_id="default",
        prompt_version="prompt-v1",
        schema_version="output-v1",
        is_cloud=True,
        envelope=ModelPayloadEnvelope(
            content=payload,
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=(),
            payload_shape="single_item",
            content_transform="raw",
        ),
        max_input_tokens=100,
        max_output_tokens=20,
        max_model_http_attempts=1,
        max_active_seconds=30,
        provider_retries_disabled=True,
        output_schema=Output,
        provider_call=provider_call,
    )
    assert result.value == "ok" and calls == 1
    async with AsyncSession(m0_engine) as session:
        budget = await session.scalar(
            select(AgentRootBudgetRecord).where(
                AgentRootBudgetRecord.budget_id == "gateway-budget"
            )
        )
        assert budget is not None
        assert budget.reserved_model_attempts == 0
        assert budget.settled_model_attempts == 1
        assert budget.settled_input_tokens == 10
        events = list(
            (
                await session.scalars(
                    select(AgentEventRecord).where(
                        AgentEventRecord.run_id == run.run_id,
                        AgentEventRecord.event_type == "step.status_changed",
                    )
                )
            ).all()
        )
        assert len(events) == 1
        assert events[0].detail_json["prompt_version"] == "prompt-v1"


@pytest.mark.asyncio
async def test_model_gateway_unknown_outcome_requires_reconciliation(
    m0_engine: AsyncEngine,
) -> None:
    await add_membership(m0_engine)
    payload = {"claim": "candidate"}
    runs = RunRuntimeService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx-1",
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
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx-1",
            task_request_id="failed-gateway-task",
            agent_type="A2",
            run_mode="standalone_confirmation",
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=1,
            next_status=RunStatus.RUNNING,
        )
        step = await runs.create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="model_extract",
            attempt=1,
            input_hash=content_hash(payload),
        )
        await runs.transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=1,
            next_status=StepStatus.RUNNING,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id="failed-gateway-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 30,
            },
        )
        await uow.commit()

    async def provider_call(_: object) -> ProviderResult:
        raise RuntimeError("transport outcome is unknown")

    with pytest.raises(RuntimeError):
        await AuthorizedModelGateway[Output](m0_engine).invoke(
            authorization_id=authorization.authorization_id,
            budget_id="failed-gateway-budget",
            research_context_id="ctx-1",
            actor_scope="local-owner",
            child_run_id=run.run_id,
            step_id=step.step_id,
            attempt=1,
            provider="provider",
            model="model",
            purpose="extract",
            profile_id="default",
            prompt_version="prompt-v1",
            schema_version="output-v1",
            is_cloud=True,
            envelope=ModelPayloadEnvelope(
                content=payload,
                content_granularity="section",
                data_categories=("document_text",),
                payload_refs=(),
                payload_shape="single_item",
                content_transform="raw",
            ),
            max_input_tokens=100,
            max_output_tokens=20,
            max_model_http_attempts=1,
            max_active_seconds=30,
            provider_retries_disabled=True,
            output_schema=Output,
            provider_call=provider_call,
        )
    async with AsyncSession(m0_engine) as session:
        failed_run = await session.get(AgentRunRecord, run.run_id)
        reservation = await session.scalar(
            select(AgentBudgetReservationRecord).where(
                AgentBudgetReservationRecord.child_run_id == run.run_id
            )
        )
        assert failed_run is not None
        assert failed_run.workflow_status == RunStatus.RECOVERY_REQUIRED
        assert reservation is not None and reservation.status == "active"


@pytest.mark.parametrize("fault_mode", ["timeout", "disconnect", "truncated"])
@pytest.mark.asyncio
async def test_model_gateway_loopback_network_faults_require_reconciliation(
    m0_engine: AsyncEngine, fault_mode: str
) -> None:
    await add_membership(m0_engine)
    payload = {"claim": "candidate"}
    runs = RunRuntimeService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            provider="loopback-provider",
            model="fault-model",
            purpose="network-fault-test",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash=content_hash(payload),
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx-1",
            task_request_id=f"network-{fault_mode}-task",
            agent_type="A2",
            run_mode="standalone_confirmation",
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=run.revision,
            next_status=RunStatus.RUNNING,
        )
        step = await runs.create_step(
            uow.session,
            run_id=run.run_id,
            step_kind="network_fault",
            attempt=1,
            input_hash=content_hash(payload),
        )
        await runs.transition_step(
            uow.session,
            step_id=step.step_id,
            expected_revision=step.revision,
            next_status=StepStatus.RUNNING,
        )
        BudgetService().create_budget(
            uow.session,
            budget_id=f"network-{fault_mode}-budget",
            root_run_id=run.run_id,
            limits={
                "model_attempts": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "model_http_attempts": 1,
                "total_http_attempts": 1,
                "active_seconds": 30,
            },
        )
        await uow.commit()

    async def fault_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            await reader.readuntil(b"\r\n\r\n")
            if fault_mode == "timeout":
                await asyncio.sleep(0.2)
            elif fault_mode == "truncated":
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 40\r\n"
                    b"Content-Type: application/json\r\n\r\n{\"value\":"
                )
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(fault_handler, "127.0.0.1", 0)
    port = int(server.sockets[0].getsockname()[1])

    async def provider_call(_: object) -> ProviderResult:
        async with httpx.AsyncClient(timeout=0.05) as client:
            response = await client.get(f"http://127.0.0.1:{port}/model")
            return ProviderResult(
                payload=response.json(), usage=ModelUsage(1, 1)
            )

    try:
        with pytest.raises(httpx.HTTPError):
            await AuthorizedModelGateway[Output](m0_engine).invoke(
                authorization_id=authorization.authorization_id,
                budget_id=f"network-{fault_mode}-budget",
                research_context_id="ctx-1",
                actor_scope="local-owner",
                child_run_id=run.run_id,
                step_id=step.step_id,
                attempt=1,
                provider="loopback-provider",
                model="fault-model",
                purpose="network-fault-test",
                profile_id="default",
                prompt_version="prompt-v1",
                schema_version="output-v1",
                is_cloud=True,
                envelope=ModelPayloadEnvelope(
                    content=payload,
                    content_granularity="section",
                    data_categories=("document_text",),
                    payload_refs=(),
                    payload_shape="single_item",
                    content_transform="raw",
                ),
                max_input_tokens=100,
                max_output_tokens=20,
                max_model_http_attempts=1,
                max_active_seconds=30,
                provider_retries_disabled=True,
                output_schema=Output,
                provider_call=provider_call,
            )
    finally:
        server.close()
        await server.wait_closed()

    async with AsyncSession(m0_engine) as session:
        failed_run = await session.get(AgentRunRecord, run.run_id)
        reservation = await session.scalar(
            select(AgentBudgetReservationRecord).where(
                AgentBudgetReservationRecord.child_run_id == run.run_id
            )
        )
        execution = await session.scalar(
            select(AgentExternalExecutionRecord).where(
                AgentExternalExecutionRecord.run_id == run.run_id
            )
        )
        assert failed_run is not None
        assert failed_run.workflow_status == RunStatus.RECOVERY_REQUIRED
        assert reservation is not None and reservation.status == "active"
        assert execution is not None and execution.state == "outcome_unknown"


@pytest.mark.asyncio
async def test_m0_api_idempotent_task_run_and_cancel(
    m0_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_membership(m0_engine)
    import app.agents.m0_router as router_module

    monkeypatch.setattr(router_module, "engine", m0_engine)
    monkeypatch.setattr(
        router_module,
        "AsyncSessionLocal",
        async_sessionmaker(m0_engine, expire_on_commit=False),
    )
    app = FastAPI()
    app.include_router(m0_router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        task_payload = {
            "research_context_id": "ctx-1",
            "requested_agent": "A1",
            "intent": "discover",
        }
        first = await client.post(
            "/agent-runtime/task-requests",
            json=task_payload,
            headers={"Idempotency-Key": "task-key"},
        )
        replay = await client.post(
            "/agent-runtime/task-requests",
            json=task_payload,
            headers={"Idempotency-Key": "task-key"},
        )
        assert first.status_code == 201 and replay.status_code == 201
        assert first.json()["task_request_id"] == replay.json()["task_request_id"]
        conflict = await client.post(
            "/agent-runtime/task-requests",
            json={**task_payload, "intent": "different"},
            headers={"Idempotency-Key": "task-key"},
        )
        assert conflict.status_code == 409

        run = await client.post(
            "/agent-runtime/runs",
            json={
                "research_context_id": "ctx-1",
                "task_request_id": first.json()["task_request_id"],
                "agent_type": "A1",
                "run_mode": "standalone_confirmation",
            },
            headers={"Idempotency-Key": "run-key"},
        )
        assert run.status_code == 201 and run.json()["status"] == "created"
        read = await client.get(f"/agent-runtime/runs/{run.json()['run_id']}")
        assert read.status_code == 200
        cancelled = await client.post(
            f"/agent-runtime/runs/{run.json()['run_id']}/cancel",
            json={"expected_revision": 1},
            headers={"Idempotency-Key": "cancel-key"},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
    async with AsyncSession(m0_engine) as session:
        stored = await session.get(AgentRunRecord, run.json()["run_id"])
        assert stored is not None and stored.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_m0_api_rejects_context_without_membership(
    m0_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.agents.m0_router as router_module

    monkeypatch.setattr(router_module, "engine", m0_engine)
    app = FastAPI()
    app.include_router(m0_router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent-runtime/task-requests",
            json={
                "research_context_id": "missing",
                "requested_agent": "A1",
                "intent": "discover",
            },
            headers={"Idempotency-Key": "missing-context"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_m0_api_run_read_requires_context_membership(
    m0_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        run = await RunRuntimeService().create_run(
            uow.session,
            research_context_id="private-context",
            task_request_id="private-task",
            agent_type="A1",
            run_mode="standalone_confirmation",
        )
        await uow.commit()
    import app.agents.m0_router as router_module

    monkeypatch.setattr(
        router_module,
        "AsyncSessionLocal",
        async_sessionmaker(m0_engine, expire_on_commit=False),
    )
    app = FastAPI()
    app.include_router(m0_router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/agent-runtime/runs/{run.run_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_m0_api_authorization_revoke_is_idempotent(
    m0_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_membership(m0_engine)
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        authorization = await AuthorizationService().issue(
            uow.session,
            research_context_id="ctx-1",
            actor_scope="local-owner",
            provider="provider",
            model="model",
            purpose="extract",
            content_granularity="section",
            data_categories=("document_text",),
            payload_refs=[],
            payload_hash="a" * 64,
            payload_shape="single_item",
            content_transform="raw",
            allow_cloud_transfer=True,
        )
        await uow.commit()
    import app.agents.m0_router as router_module

    monkeypatch.setattr(router_module, "engine", m0_engine)
    app = FastAPI()
    app.include_router(m0_router)
    url = f"/agent-runtime/model-authorizations/{authorization.authorization_id}/revoke"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            url,
            json={"expected_revision": 1},
            headers={"Idempotency-Key": "revoke-key"},
        )
        replay = await client.post(
            url,
            json={"expected_revision": 1},
            headers={"Idempotency-Key": "revoke-key"},
        )
        missing_key = await client.post(url, json={"expected_revision": 2})
    assert first.status_code == 200 and replay.status_code == 200
    assert first.json()["revision"] == replay.json()["revision"] == 2
    assert missing_key.status_code == 422


@pytest.mark.asyncio
async def test_m0_api_recovery_is_explicit_and_idempotent(
    m0_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_membership(m0_engine)
    runs = RunRuntimeService()
    async with ImmediateUnitOfWork(m0_engine) as uow:
        assert uow.session is not None
        run = await runs.create_run(
            uow.session,
            research_context_id="ctx-1",
            task_request_id="recovery-task",
            agent_type="A2",
            run_mode="standalone_confirmation",
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=1,
            next_status=RunStatus.RUNNING,
        )
        run = await runs.transition_run(
            uow.session,
            run_id=run.run_id,
            expected_revision=2,
            next_status=RunStatus.RECOVERY_REQUIRED,
            reason_code="external_request_outcome_unknown",
        )
        await uow.commit()
    import app.agents.m0_router as router_module

    monkeypatch.setattr(router_module, "engine", m0_engine)
    app = FastAPI()
    app.include_router(m0_router)
    url = f"/agent-runtime/runs/{run.run_id}/recover"
    request = {
        "expected_revision": 3,
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            url, json=request, headers={"Idempotency-Key": "recover-key"}
        )
        replay = await client.post(
            url, json=request, headers={"Idempotency-Key": "recover-key"}
        )
    assert first.status_code == 200 and replay.status_code == 200
    assert first.json()["status"] == "running"
    assert first.json()["revision"] == replay.json()["revision"] == 4

