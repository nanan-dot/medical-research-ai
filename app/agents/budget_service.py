"""Concurrent root-budget reservation and settlement with frozen counters."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.budget_model import AgentBudgetReservationRecord, AgentRootBudgetRecord
from app.agents.errors import BudgetExhaustedError, RevisionConflictError
from app.agents.model import AgentRunRecord
from app.agents.outbox_service import OutboxService
from app.agents.runtime_model import AgentStepRecord

COUNTER_NAMES = (
    "model_attempts",
    "input_tokens",
    "output_tokens",
    "retrieval_http_attempts",
    "model_http_attempts",
    "other_http_attempts",
    "total_http_attempts",
    "logical_tool_calls",
    "active_seconds",
)
DB_NAMES = {
    "retrieval_http_attempts": "retrieval_http",
    "total_http_attempts": "total_http",
    "logical_tool_calls": "tool_calls",
}


def _db_name(name: str) -> str:
    return DB_NAMES.get(name, name)


def _normalized(values: dict[str, int]) -> dict[str, int]:
    unknown = set(values) - set(COUNTER_NAMES)
    if unknown:
        raise ValueError(f"unknown budget counters: {sorted(unknown)}")
    result = {name: int(values.get(name, 0)) for name in COUNTER_NAMES}
    if any(value < 0 for value in result.values()):
        raise ValueError("budget counters cannot be negative")
    expected_total = sum(
        result[name]
        for name in (
            "retrieval_http_attempts",
            "model_http_attempts",
            "other_http_attempts",
        )
    )
    if result["total_http_attempts"] != expected_total:
        raise ValueError("total_http_attempts must equal retrieval + model + other")
    return result


class BudgetService:
    def __init__(self, outbox: OutboxService | None = None) -> None:
        self._outbox = outbox or OutboxService()

    def create_budget(
        self,
        session: AsyncSession,
        *,
        budget_id: str,
        root_run_id: str,
        limits: dict[str, int],
        max_active_seconds: int | None = None,
    ) -> AgentRootBudgetRecord:
        values = dict(limits)
        if max_active_seconds is not None:
            values["active_seconds"] = max_active_seconds
        normalized = _normalized(values)
        fields: dict[str, object] = {
            "budget_id": budget_id,
            "root_run_id": root_run_id,
            "revision": 1,
        }
        for name, amount in normalized.items():
            db_name = _db_name(name)
            fields[f"max_{db_name}"] = amount
            fields[f"reserved_{db_name}"] = 0
            fields[f"settled_{db_name}"] = 0
        budget = AgentRootBudgetRecord(**fields)
        session.add(budget)
        return budget

    async def reserve(
        self,
        session: AsyncSession,
        *,
        budget_id: str,
        child_run_id: str,
        step_id: str,
        attempt: int,
        provider: str,
        requested: dict[str, int],
        request_fingerprint: str,
    ) -> AgentBudgetReservationRecord:
        existing = await session.scalar(
            select(AgentBudgetReservationRecord).where(
                AgentBudgetReservationRecord.step_id == step_id,
                AgentBudgetReservationRecord.attempt == attempt,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != request_fingerprint:
                raise RevisionConflictError("reservation attempt was reused")
            return existing
        budget = await session.get(AgentRootBudgetRecord, budget_id)
        run = await session.get(AgentRunRecord, child_run_id)
        step = await session.get(AgentStepRecord, step_id)
        if budget is None:
            raise KeyError(budget_id)
        if (
            run is None
            or step is None
            or step.run_id != child_run_id
            or step.attempt != attempt
            or run.root_run_id != budget.root_run_id
        ):
            raise ValueError("budget, child Run and Step do not share one root")
        normalized = _normalized(requested)
        update_values: dict[str, object] = {
            "revision": AgentRootBudgetRecord.revision + 1
        }
        for name, amount in normalized.items():
            db_name = _db_name(name)
            reserved = int(getattr(budget, f"reserved_{db_name}"))
            settled = int(getattr(budget, f"settled_{db_name}"))
            maximum = int(getattr(budget, f"max_{db_name}"))
            if reserved + settled + amount > maximum:
                raise BudgetExhaustedError(name)
            update_values[f"reserved_{db_name}"] = (
                getattr(AgentRootBudgetRecord, f"reserved_{db_name}") + amount
            )
        result = await session.execute(
            update(AgentRootBudgetRecord)
            .where(
                AgentRootBudgetRecord.budget_id == budget_id,
                AgentRootBudgetRecord.revision == budget.revision,
            )
            .values(**update_values)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        fields: dict[str, object] = {
            "reservation_id": str(uuid4()),
            "budget_id": budget_id,
            "child_run_id": child_run_id,
            "step_id": step_id,
            "attempt": attempt,
            "provider": provider,
            "status": "active",
            "request_fingerprint": request_fingerprint,
            "created_at": datetime.now(UTC),
            "settled_at": None,
        }
        for name, amount in normalized.items():
            db_name = _db_name(name)
            fields[f"reserved_{db_name}"] = amount
            fields[f"actual_{db_name}"] = 0
        reservation = AgentBudgetReservationRecord(**fields)
        session.add(reservation)
        self._outbox.add(
            session,
            aggregate_type="budget",
            aggregate_id=budget_id,
            event_type="budget.reserved",
            payload={
                "reservation_id": reservation.reservation_id,
                "requested": normalized,
            },
        )
        await session.flush()
        return reservation

    async def settle(
        self,
        session: AsyncSession,
        *,
        reservation_id: str,
        actual: dict[str, int],
    ) -> AgentBudgetReservationRecord:
        reservation = await session.get(AgentBudgetReservationRecord, reservation_id)
        if reservation is None:
            raise KeyError(reservation_id)
        normalized = _normalized(actual)
        if reservation.status == "settled":
            if any(
                int(getattr(reservation, f"actual_{_db_name(name)}")) != amount
                for name, amount in normalized.items()
            ):
                raise RevisionConflictError("settlement differs from stored result")
            return reservation
        if reservation.status != "active":
            raise RevisionConflictError("reservation is not active")
        budget = await session.get(AgentRootBudgetRecord, reservation.budget_id)
        assert budget is not None
        changes: dict[str, object] = {"revision": AgentRootBudgetRecord.revision + 1}
        for name, amount in normalized.items():
            db_name = _db_name(name)
            reserved = int(getattr(reservation, f"reserved_{db_name}"))
            if amount > reserved:
                raise BudgetExhaustedError("actual usage exceeds reservation")
            changes[f"reserved_{db_name}"] = (
                getattr(AgentRootBudgetRecord, f"reserved_{db_name}") - reserved
            )
            changes[f"settled_{db_name}"] = (
                getattr(AgentRootBudgetRecord, f"settled_{db_name}") + amount
            )
        result = await session.execute(
            update(AgentRootBudgetRecord)
            .where(
                AgentRootBudgetRecord.budget_id == budget.budget_id,
                AgentRootBudgetRecord.revision == budget.revision,
            )
            .values(**changes)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        for name, amount in normalized.items():
            setattr(reservation, f"actual_{_db_name(name)}", amount)
        reservation.status = "settled"
        reservation.settled_at = datetime.now(UTC)
        self._outbox.add(
            session,
            aggregate_type="budget",
            aggregate_id=budget.budget_id,
            event_type="budget.settled",
            payload={
                "reservation_id": reservation_id,
                "status": "settled",
                "actual": normalized,
            },
        )
        await session.flush()
        return reservation

    async def release(
        self, session: AsyncSession, *, reservation_id: str
    ) -> AgentBudgetReservationRecord:
        reservation = await session.get(AgentBudgetReservationRecord, reservation_id)
        if reservation is None:
            raise KeyError(reservation_id)
        if reservation.status == "released":
            return reservation
        if reservation.status != "active":
            raise RevisionConflictError("only an active reservation can be released")
        budget = await session.get(AgentRootBudgetRecord, reservation.budget_id)
        assert budget is not None
        changes: dict[str, object] = {"revision": AgentRootBudgetRecord.revision + 1}
        for name in COUNTER_NAMES:
            db_name = _db_name(name)
            amount = int(getattr(reservation, f"reserved_{db_name}"))
            changes[f"reserved_{db_name}"] = (
                getattr(AgentRootBudgetRecord, f"reserved_{db_name}") - amount
            )
        result = await session.execute(
            update(AgentRootBudgetRecord)
            .where(
                AgentRootBudgetRecord.budget_id == budget.budget_id,
                AgentRootBudgetRecord.revision == budget.revision,
            )
            .values(**changes)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        reservation.status = "released"
        reservation.settled_at = datetime.now(UTC)
        await session.flush()
        return reservation
