"""M0 公共运行时 HTTP API。"""

from datetime import timedelta
from typing import Annotated, NoReturn

from fastapi import APIRouter, Header, HTTPException, status

from app.agents.artifact_service import ArtifactService
from app.agents.authorization_model import ModelTransferAuthorizationRecord
from app.agents.authorization_service import AuthorizationService
from app.agents.confirmation_model import RoleDecisionRecord, UserConfirmationRecord
from app.agents.confirmation_service import ConfirmationService
from app.agents.errors import (
    AgentInfrastructureError,
    PermissionDeniedError,
)
from app.agents.hash_schema import content_hash
from app.agents.idempotency_service import IdempotencyService
from app.agents.m0_api_schemas import (
    ArtifactResolveRead,
    ArtifactResolveRequest,
    AuthorizationCreateRequest,
    AuthorizationRead,
    AuthorizationRevokeRequest,
    ConfirmationCreateRequest,
    ConfirmationDecisionRequest,
    ConfirmationRead,
    DecisionRead,
    RuntimeCancelRequest,
    RuntimeRecoveryRequest,
    RuntimeRunCreateRequest,
    RuntimeRunRead,
    TaskCreateRequest,
    TaskRead,
)
from app.agents.model import AgentRunRecord
from app.agents.permission_service import LOCAL_OWNER, PermissionService
from app.agents.recovery_service import RecoveryService
from app.agents.run_runtime_service import RunRuntimeService
from app.agents.runtime_model import AgentTaskRequestRecord
from app.agents.task_request_service import TaskRequestService
from app.agents.transaction import ImmediateUnitOfWork
from app.core.database import AsyncSessionLocal, engine

router = APIRouter(prefix="/agent-runtime", tags=["Agent 公共运行时"])
IdempotencyHeader = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
]


def _http_error(error: Exception) -> NoReturn:
    if isinstance(error, PermissionDeniedError):
        raise HTTPException(status_code=403, detail=error.code) from error
    if isinstance(error, KeyError):
        raise HTTPException(status_code=404, detail="resource_not_found") from error
    if isinstance(error, AgentInfrastructureError):
        raise HTTPException(status_code=409, detail=error.code) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


def _run_read(run: AgentRunRecord) -> RuntimeRunRead:
    return RuntimeRunRead(
        run_id=run.run_id,
        research_context_id=run.research_context_id,
        task_request_id=run.task_request_id,
        agent_type=run.agent_type,
        run_mode=run.run_mode,
        status=run.workflow_status,
        phase=run.phase,
        reason_code=run.reason_code,
        revision=run.revision,
    )


@router.post(
    "/task-requests", response_model=TaskRead, status_code=status.HTTP_201_CREATED
)
async def create_task_request(
    payload: TaskCreateRequest, idempotency_key: IdempotencyHeader
) -> TaskRead:
    context_id = str(payload.research_context_id)
    request_payload = payload.model_dump(mode="json")
    request_digest = content_hash(request_payload)
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="create_task_request",
                key=idempotency_key,
                request_hash=request_digest,
            )
            if replay is not None:
                record = await uow.session.get(
                    AgentTaskRequestRecord, replay.resource_id
                )
                if record is None:
                    raise KeyError(replay.resource_id)
                await uow.commit()
                return TaskRead(
                    task_request_id=record.task_request_id,
                    research_context_id=record.research_context_id,
                    requested_agent=record.requested_agent,
                    intent=record.intent,
                    request_hash=record.request_hash,
                )
            task = await TaskRequestService().create(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                requested_agent=payload.requested_agent,
                intent=payload.intent,
                input_refs=tuple(payload.input_artifact_refs),
                authorization_refs=tuple(payload.authorization_refs),
            )
            idem.add(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="create_task_request",
                key=idempotency_key,
                request_hash=request_digest,
                resource_type="task_request",
                resource_id=task.task_request_id,
                resource_version=task.request_hash,
            )
            await uow.commit()
            return TaskRead(
                task_request_id=task.task_request_id,
                research_context_id=task.research_context_id,
                requested_agent=task.requested_agent,
                intent=task.intent,
                request_hash=task.request_hash,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post(
    "/runs", response_model=RuntimeRunRead, status_code=status.HTTP_201_CREATED
)
async def create_runtime_run(
    payload: RuntimeRunCreateRequest, idempotency_key: IdempotencyHeader
) -> RuntimeRunRead:
    context_id = str(payload.research_context_id)
    digest = content_hash(payload.model_dump(mode="json"))
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            await PermissionService().require_membership(
                uow.session, context_id, LOCAL_OWNER
            )
            task = await uow.session.get(
                AgentTaskRequestRecord, payload.task_request_id
            )
            if task is None or task.research_context_id != context_id:
                raise KeyError(payload.task_request_id)
            if task.requested_agent != payload.agent_type:
                raise ValueError("agent_type must match TaskRequest.requested_agent")
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="create_run",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is not None:
                run = await uow.session.get(AgentRunRecord, replay.resource_id)
                if run is None:
                    raise KeyError(replay.resource_id)
                await uow.commit()
                return _run_read(run)
            runs = RunRuntimeService()
            run = await runs.create_run(
                uow.session,
                research_context_id=context_id,
                task_request_id=payload.task_request_id,
                agent_type=payload.agent_type,
                run_mode=payload.run_mode,
            )
            await runs.create_step(
                uow.session,
                run_id=run.run_id,
                step_kind="initialize",
                attempt=1,
                input_hash=task.request_hash,
            )
            idem.add(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="create_run",
                key=idempotency_key,
                request_hash=digest,
                resource_type="run",
                resource_id=run.run_id,
                resource_version=str(run.revision),
            )
            await uow.commit()
            return _run_read(run)
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.get("/runs/{run_id}", response_model=RuntimeRunRead)
async def read_runtime_run(run_id: str) -> RuntimeRunRead:
    try:
        async with AsyncSessionLocal() as session:
            run = await session.get(AgentRunRecord, run_id)
            if run is None or run.is_legacy or run.research_context_id is None:
                raise KeyError(run_id)
            await PermissionService().require_membership(
                session, run.research_context_id, LOCAL_OWNER
            )
            return _run_read(run)
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post("/runs/{run_id}/cancel", response_model=RuntimeRunRead)
async def cancel_runtime_run(
    run_id: str, payload: RuntimeCancelRequest, idempotency_key: IdempotencyHeader
) -> RuntimeRunRead:
    digest = content_hash({"run_id": run_id, **payload.model_dump(mode="json")})
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            run = await uow.session.get(AgentRunRecord, run_id)
            if run is None or run.research_context_id is None:
                raise KeyError(run_id)
            await PermissionService().require_membership(
                uow.session, run.research_context_id, LOCAL_OWNER
            )
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=run.research_context_id,
                actor_scope=LOCAL_OWNER,
                action="cancel_run",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is None:
                _, run = await RunRuntimeService().cancel_run(
                    uow.session,
                    run_id=run_id,
                    expected_revision=payload.expected_revision,
                )
                if run.research_context_id is None:
                    raise ValueError("structured run requires research context")
                idem.add(
                    uow.session,
                    research_context_id=run.research_context_id,
                    actor_scope=LOCAL_OWNER,
                    action="cancel_run",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="run",
                    resource_id=run_id,
                    resource_version=str(run.revision),
                )
            await uow.commit()
            return _run_read(run)
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post("/runs/{run_id}/recover", response_model=RuntimeRunRead)
async def recover_runtime_run(
    run_id: str,
    payload: RuntimeRecoveryRequest,
    idempotency_key: IdempotencyHeader,
) -> RuntimeRunRead:
    digest = content_hash({"run_id": run_id, **payload.model_dump(mode="json")})
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            run = await uow.session.get(AgentRunRecord, run_id)
            if run is None or run.research_context_id is None:
                raise KeyError(run_id)
            await PermissionService().require_membership(
                uow.session, run.research_context_id, LOCAL_OWNER
            )
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=run.research_context_id,
                actor_scope=LOCAL_OWNER,
                action="recover_run",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is None:
                run = await RecoveryService().recover(
                    uow.session,
                    run_id=run_id,
                    expected_revision=payload.expected_revision,
                )
                if run.research_context_id is None:
                    raise ValueError("structured run requires research context")
                idem.add(
                    uow.session,
                    research_context_id=run.research_context_id,
                    actor_scope=LOCAL_OWNER,
                    action="recover_run",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="run",
                    resource_id=run_id,
                    resource_version=str(run.revision),
                )
            await uow.commit()
            return _run_read(run)
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post(
    "/confirmations",
    response_model=ConfirmationRead,
    status_code=status.HTTP_201_CREATED,
)
async def request_confirmation(
    payload: ConfirmationCreateRequest, idempotency_key: IdempotencyHeader
) -> ConfirmationRead:
    context_id = str(payload.research_context_id)
    digest = content_hash(payload.model_dump(mode="json"))
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="request_confirmation",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is not None:
                confirmation = await uow.session.get(
                    UserConfirmationRecord, replay.resource_id
                )
                if confirmation is None:
                    raise KeyError(replay.resource_id)
            else:
                confirmation = await ConfirmationService().request(
                    uow.session,
                    research_context_id=context_id,
                    actor_scope=LOCAL_OWNER,
                    action=payload.action,
                    target_refs=tuple(payload.target_refs),
                    expected_revisions=payload.expected_revisions,
                    expires_in=timedelta(seconds=payload.expires_in_seconds),
                )
                idem.add(
                    uow.session,
                    research_context_id=context_id,
                    actor_scope=LOCAL_OWNER,
                    action="request_confirmation",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="confirmation",
                    resource_id=confirmation.confirmation_id,
                    resource_version=str(confirmation.revision),
                )
            await uow.commit()
            return ConfirmationRead(
                confirmation_id=confirmation.confirmation_id,
                binding_hash=confirmation.binding_hash,
                status=confirmation.status,
                revision=confirmation.revision,
                expires_at=confirmation.expires_at,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post("/confirmations/{confirmation_id}/decisions", response_model=DecisionRead)
async def decide_confirmation(
    confirmation_id: str,
    payload: ConfirmationDecisionRequest,
    idempotency_key: IdempotencyHeader,
) -> DecisionRead:
    digest = content_hash(
        {"confirmation_id": confirmation_id, **payload.model_dump(mode="json")}
    )
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            confirmation = await uow.session.get(
                UserConfirmationRecord, confirmation_id
            )
            if confirmation is None:
                raise KeyError(confirmation_id)
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=confirmation.research_context_id,
                actor_scope=LOCAL_OWNER,
                action="decide_confirmation",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is not None:
                decision = await uow.session.get(RoleDecisionRecord, replay.resource_id)
                if decision is None:
                    raise KeyError(replay.resource_id)
            else:
                decision = await ConfirmationService().consume(
                    uow.session,
                    confirmation_id=confirmation_id,
                    expected_revision=payload.expected_revision,
                    actor_scope=LOCAL_OWNER,
                    decision=payload.decision,
                    reason=payload.reason,
                )
                idem.add(
                    uow.session,
                    research_context_id=confirmation.research_context_id,
                    actor_scope=LOCAL_OWNER,
                    action="decide_confirmation",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="role_decision",
                    resource_id=decision.decision_id,
                    resource_version=decision.version_id,
                )
            await uow.commit()
            return DecisionRead(
                decision_id=decision.decision_id,
                version_id=decision.version_id,
                content_hash=decision.content_hash,
                decision=decision.decision,
                authorized_role=decision.authorized_role,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post(
    "/model-authorizations",
    response_model=AuthorizationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_authorization(
    payload: AuthorizationCreateRequest, idempotency_key: IdempotencyHeader
) -> AuthorizationRead:
    context_id = str(payload.research_context_id)
    digest = content_hash(payload.model_dump(mode="json"))
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=context_id,
                actor_scope=LOCAL_OWNER,
                action="create_model_authorization",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is not None:
                authorization = await uow.session.get(
                    ModelTransferAuthorizationRecord,
                    replay.resource_id,
                )
                if authorization is None:
                    raise KeyError(replay.resource_id)
            else:
                authorization = await AuthorizationService().issue(
                    uow.session,
                    research_context_id=context_id,
                    actor_scope=LOCAL_OWNER,
                    provider=payload.provider,
                    model=payload.model,
                    purpose=payload.purpose,
                    content_granularity=payload.content_granularity,
                    data_categories=tuple(payload.data_categories),
                    payload_refs=payload.payload_refs,
                    payload_hash=payload.payload_hash,
                    payload_shape=payload.payload_shape,
                    content_transform=payload.content_transform,
                    allow_cloud_transfer=payload.allow_cloud_transfer,
                    expires_in=timedelta(seconds=payload.expires_in_seconds),
                )
                idem.add(
                    uow.session,
                    research_context_id=context_id,
                    actor_scope=LOCAL_OWNER,
                    action="create_model_authorization",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="model_authorization",
                    resource_id=authorization.authorization_id,
                    resource_version=str(authorization.revision),
                )
            await uow.commit()
            return AuthorizationRead(
                authorization_id=authorization.authorization_id,
                status=authorization.status,
                revision=authorization.revision,
                expires_at=authorization.expires_at,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post(
    "/model-authorizations/{authorization_id}/revoke", response_model=AuthorizationRead
)
async def revoke_model_authorization(
    authorization_id: str,
    payload: AuthorizationRevokeRequest,
    idempotency_key: IdempotencyHeader,
) -> AuthorizationRead:
    digest = content_hash(
        {"authorization_id": authorization_id, **payload.model_dump(mode="json")}
    )
    try:
        async with ImmediateUnitOfWork(engine) as uow:
            assert uow.session is not None
            authorization = await uow.session.get(
                ModelTransferAuthorizationRecord, authorization_id
            )
            if authorization is None:
                raise KeyError(authorization_id)
            await PermissionService().require_membership(
                uow.session, authorization.research_context_id, LOCAL_OWNER
            )
            idem = IdempotencyService()
            replay = await idem.find(
                uow.session,
                research_context_id=authorization.research_context_id,
                actor_scope=LOCAL_OWNER,
                action="revoke_model_authorization",
                key=idempotency_key,
                request_hash=digest,
            )
            if replay is None:
                authorization = await AuthorizationService().revoke(
                    uow.session,
                    authorization_id=authorization_id,
                    expected_revision=payload.expected_revision,
                    actor_scope=LOCAL_OWNER,
                )
                idem.add(
                    uow.session,
                    research_context_id=authorization.research_context_id,
                    actor_scope=LOCAL_OWNER,
                    action="revoke_model_authorization",
                    key=idempotency_key,
                    request_hash=digest,
                    resource_type="model_authorization",
                    resource_id=authorization_id,
                    resource_version=str(authorization.revision),
                )
            await uow.commit()
            return AuthorizationRead(
                authorization_id=authorization.authorization_id,
                status=authorization.status,
                revision=authorization.revision,
                expires_at=authorization.expires_at,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)


@router.post("/artifacts/resolve", response_model=ArtifactResolveRead)
async def resolve_artifact(payload: ArtifactResolveRequest) -> ArtifactResolveRead:
    try:
        async with AsyncSessionLocal() as session:
            await PermissionService().require_membership(
                session, str(payload.research_context_id), LOCAL_OWNER
            )
            record = await ArtifactService().resolve(
                session,
                payload.artifact_ref,
                research_context_id=str(payload.research_context_id),
            )
            return ArtifactResolveRead(
                artifact_ref=ArtifactService._ref(record),
                typed_ref=record.typed_ref_json,
            )
    except Exception as error:  # noqa: BLE001 - centralized HTTP error mapping
        _http_error(error)
