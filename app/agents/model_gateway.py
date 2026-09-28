"""Model gateway enforcing authorization, budget and send-boundary recovery."""

import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.agents.authorization_contract import normalize_authorization_scope
from app.agents.authorization_service import AuthorizationService
from app.agents.budget_service import BudgetService
from app.agents.contracts import AgentEventPayload, ArtifactRef
from app.agents.enums import TERMINAL_RUN_STATUSES, RunStatus, StepStatus
from app.agents.errors import InvalidStateTransitionError
from app.agents.external_execution_service import ExternalExecutionService
from app.agents.hash_schema import content_hash
from app.agents.model import AgentRunRecord
from app.agents.run_runtime_service import RunRuntimeService
from app.agents.runtime_model import AgentExternalExecutionRecord, AgentStepRecord
from app.agents.transaction import ImmediateUnitOfWork


@dataclass(frozen=True)
class ModelPayloadEnvelope:
    content: object
    content_granularity: str
    data_categories: tuple[str, ...]
    payload_refs: tuple[ArtifactRef, ...]
    payload_shape: str
    content_transform: str

    def validate(self) -> None:
        if self.payload_shape not in {"single_item", "multi_item_bundle"}:
            raise ValueError("invalid payload_shape")
        if self.content_transform not in {"raw", "deidentified", "aggregated"}:
            raise ValueError("invalid content_transform")
        normalize_authorization_scope(self.content_granularity, self.data_categories)
        if self.payload_shape == "single_item" and len(self.payload_refs) > 1:
            raise ValueError("single_item payload cannot contain multiple refs")
        if self.payload_shape == "multi_item_bundle" and len(self.payload_refs) < 2:
            raise ValueError("multi_item_bundle requires multiple refs")


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    model_http_attempts: int = 1


@dataclass(frozen=True)
class ProviderResult:
    payload: object
    usage: ModelUsage


ProviderCall = Callable[[object], Awaitable[ProviderResult]]


class AuthorizedModelGateway[OutputT: BaseModel]:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        authorization: AuthorizationService | None = None,
        budgets: BudgetService | None = None,
        runs: RunRuntimeService | None = None,
        executions: ExternalExecutionService | None = None,
        before_send_checkpoint: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._engine = engine
        self._authorization = authorization or AuthorizationService()
        self._budgets = budgets or BudgetService()
        self._runs = runs or RunRuntimeService()
        self._executions = executions or ExternalExecutionService()
        self._before_send_checkpoint = before_send_checkpoint

    async def invoke(
        self,
        *,
        authorization_id: str,
        budget_id: str,
        research_context_id: str,
        actor_scope: str,
        child_run_id: str,
        step_id: str,
        attempt: int,
        provider: str,
        model: str,
        purpose: str,
        profile_id: str,
        prompt_version: str,
        schema_version: str,
        is_cloud: bool,
        envelope: ModelPayloadEnvelope,
        max_input_tokens: int,
        max_output_tokens: int,
        max_model_http_attempts: int,
        max_active_seconds: int,
        provider_retries_disabled: bool,
        output_schema: type[OutputT],
        provider_call: ProviderCall,
        expected_artifact_type: str | None = None,
        expected_artifact_key: str | None = None,
    ) -> OutputT:
        envelope.validate()
        if not provider_retries_disabled:
            raise ValueError("provider SDK hidden retries must be disabled")
        if max_model_http_attempts < 1 or max_active_seconds < 0:
            raise ValueError("invalid model-call budget")
        payload_digest = content_hash(envelope.content)
        fingerprint = content_hash(
            {
                "authorization_id": authorization_id,
                "payload_hash": payload_digest,
                "provider": provider,
                "model": model,
                "purpose": purpose,
                "max_model_http_attempts": max_model_http_attempts,
            }
        )
        async with ImmediateUnitOfWork(self._engine) as uow:
            assert uow.session is not None
            await self._assert_running(
                uow.session, child_run_id, step_id, attempt, research_context_id
            )
            await self._assert_authorized(
                uow.session,
                authorization_id,
                research_context_id,
                actor_scope,
                provider,
                model,
                purpose,
                payload_digest,
                envelope,
                is_cloud,
            )
            reservation = await self._budgets.reserve(
                uow.session,
                budget_id=budget_id,
                child_run_id=child_run_id,
                step_id=step_id,
                attempt=attempt,
                provider=provider,
                requested={
                    "model_attempts": 1,
                    "input_tokens": max_input_tokens,
                    "output_tokens": max_output_tokens,
                    "model_http_attempts": max_model_http_attempts,
                    "total_http_attempts": max_model_http_attempts,
                    "active_seconds": max_active_seconds,
                },
                request_fingerprint=fingerprint,
            )
            execution = await self._executions.prepare(
                uow.session,
                run_id=child_run_id,
                step_id=step_id,
                attempt=attempt,
                request_fingerprint=fingerprint,
                authorization_id=authorization_id,
                reservation_id=reservation.reservation_id,
                expected_artifact_type=expected_artifact_type,
                expected_artifact_key=expected_artifact_key,
            )
            reservation_id = reservation.reservation_id
            execution_id = execution.execution_id
            await uow.commit()

        if self._before_send_checkpoint is not None:
            await self._before_send_checkpoint()
        try:
            async with ImmediateUnitOfWork(self._engine) as uow:
                assert uow.session is not None
                await self._assert_running(
                    uow.session, child_run_id, step_id, attempt, research_context_id
                )
                await self._assert_authorized(
                    uow.session,
                    authorization_id,
                    research_context_id,
                    actor_scope,
                    provider,
                    model,
                    purpose,
                    payload_digest,
                    envelope,
                    is_cloud,
                )
                # The committed prepared -> sent transition is the send
                # linearization point. After this commit recovery must assume
                # the provider may have received the request, even if the
                # following network call has not returned locally.
                await self._executions.transition(
                    uow.session,
                    execution_id=execution_id,
                    expected_revision=1,
                    expected_state="prepared",
                    next_state="sent",
                )
                await uow.commit()
        except Exception:
            async with ImmediateUnitOfWork(self._engine) as release_uow:
                assert release_uow.session is not None
                stored = await release_uow.session.get(
                    AgentExternalExecutionRecord, execution_id
                )
                if stored is not None and stored.state == "prepared":
                    await self._executions.transition(
                        release_uow.session,
                        execution_id=execution_id,
                        expected_revision=stored.revision,
                        expected_state="prepared",
                        next_state="failed_before_send",
                    )
                await self._budgets.release(
                    release_uow.session, reservation_id=reservation_id
                )
                await release_uow.commit()
            raise

        started = time.monotonic()
        try:
            result = await provider_call(envelope.content)
        except Exception:
            async with ImmediateUnitOfWork(self._engine) as recovery_uow:
                assert recovery_uow.session is not None
                await self._executions.transition(
                    recovery_uow.session,
                    execution_id=execution_id,
                    expected_revision=2,
                    expected_state="sent",
                    next_state="outcome_unknown",
                )
                current = await recovery_uow.session.get(AgentRunRecord, child_run_id)
                if (
                    current is not None
                    and RunStatus(current.workflow_status) not in TERMINAL_RUN_STATUSES
                ):
                    await self._runs.transition_run(
                        recovery_uow.session,
                        run_id=child_run_id,
                        expected_revision=current.revision,
                        next_status=RunStatus.RECOVERY_REQUIRED,
                        reason_code="model_call_outcome_unknown",
                    )
                await recovery_uow.commit()
            raise
        elapsed = math.ceil(time.monotonic() - started)
        if result.usage.model_http_attempts > max_model_http_attempts:
            raise ValueError("provider reported more HTTP attempts than reserved")
        validation_error: Exception | None = None
        parsed: OutputT | None = None
        try:
            parsed = output_schema.model_validate(result.payload)
        except Exception as exc:  # noqa: BLE001 - retain schema validation error
            validation_error = exc
        async with ImmediateUnitOfWork(self._engine) as uow:
            assert uow.session is not None
            await self._executions.transition(
                uow.session,
                execution_id=execution_id,
                expected_revision=2,
                expected_state="sent",
                next_state="succeeded",
                result_payload_hash=content_hash(result.payload),
            )
            await self._budgets.settle(
                uow.session,
                reservation_id=reservation_id,
                actual={
                    "model_attempts": 1,
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "model_http_attempts": result.usage.model_http_attempts,
                    "total_http_attempts": result.usage.model_http_attempts,
                    "active_seconds": elapsed,
                },
            )
            await self._runs.append_event(
                uow.session,
                run_id=child_run_id,
                step_id=step_id,
                event_type="step.status_changed",
                payload=AgentEventPayload(
                    detail_kind="model_call",
                    detail={
                        "authorization_id": authorization_id,
                        "reservation_id": reservation_id,
                        "provider": provider,
                        "model": model,
                        "purpose": purpose,
                        "profile_id": profile_id,
                        "prompt_version": prompt_version,
                        "schema_version": schema_version,
                        "status": "schema_invalid" if validation_error else "completed",
                        "input_tokens": result.usage.input_tokens,
                        "output_tokens": result.usage.output_tokens,
                        "total_http": result.usage.model_http_attempts,
                    },
                ),
            )
            await uow.commit()
        if validation_error is not None:
            raise validation_error
        assert parsed is not None
        return parsed

    async def _assert_authorized(
        self,
        session: AsyncSession,
        authorization_id: str,
        research_context_id: str,
        actor_scope: str,
        provider: str,
        model: str,
        purpose: str,
        payload_digest: str,
        envelope: ModelPayloadEnvelope,
        is_cloud: bool,
    ) -> None:
        await self._authorization.assert_allowed(
            session,
            authorization_id=authorization_id,
            research_context_id=research_context_id,
            actor_scope=actor_scope,
            provider=provider,
            model=model,
            purpose=purpose,
            content_granularity=envelope.content_granularity,
            data_categories=envelope.data_categories,
            payload_refs=envelope.payload_refs,
            payload_hash=payload_digest,
            payload_shape=envelope.payload_shape,
            content_transform=envelope.content_transform,
            is_cloud=is_cloud,
        )

    @staticmethod
    async def _assert_running(
        session: AsyncSession, run_id: str, step_id: str, attempt: int, context_id: str
    ) -> None:
        run = await session.get(AgentRunRecord, run_id)
        step = await session.get(AgentStepRecord, step_id)
        if (
            run is None
            or run.research_context_id != context_id
            or RunStatus(run.workflow_status) != RunStatus.RUNNING
            or step is None
            or step.run_id != run_id
            or StepStatus(step.status) != StepStatus.RUNNING
            or step.attempt != attempt
        ):
            raise InvalidStateTransitionError(
                "model call requires matching running Run and Step"
            )
