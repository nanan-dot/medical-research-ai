"""根预算、预留和结算模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentRootBudgetRecord(Base):
    __tablename__ = "agent_root_budgets"
    __table_args__ = tuple(
        CheckConstraint(f"{column} >= 0", name=f"ck_root_budget_{column}_nonnegative")
        for column in (
            "max_model_attempts",
            "max_input_tokens",
            "max_output_tokens",
            "max_retrieval_http",
            "max_total_http",
            "max_tool_calls",
            "max_active_seconds",
            "max_model_http_attempts",
            "max_other_http_attempts",
            "reserved_model_attempts",
            "settled_model_attempts",
            "reserved_input_tokens",
            "settled_input_tokens",
            "reserved_output_tokens",
            "settled_output_tokens",
            "reserved_retrieval_http",
            "settled_retrieval_http",
            "reserved_total_http",
            "settled_total_http",
            "reserved_tool_calls",
            "settled_tool_calls",
            "reserved_model_http_attempts",
            "settled_model_http_attempts",
            "reserved_other_http_attempts",
            "settled_other_http_attempts",
            "reserved_active_seconds",
            "settled_active_seconds",
        )
    ) + tuple(
        CheckConstraint(
            f"reserved_{name} + settled_{name} <= max_{name}",
            name=f"ck_root_budget_{name}_within_limit",
        )
        for name in (
            "model_attempts",
            "input_tokens",
            "output_tokens",
            "retrieval_http",
            "total_http",
            "tool_calls",
            "model_http_attempts",
            "other_http_attempts",
            "active_seconds",
        )
    ) + (
        CheckConstraint(
            "reserved_total_http = reserved_retrieval_http + "
            "reserved_model_http_attempts + reserved_other_http_attempts",
            name="ck_root_budget_reserved_http_conservation",
        ),
        CheckConstraint(
            "settled_total_http = settled_retrieval_http + "
            "settled_model_http_attempts + settled_other_http_attempts",
            name="ck_root_budget_settled_http_conservation",
        ),
    )

    budget_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    root_run_id: Mapped[str] = mapped_column(String(64), unique=True)
    max_model_attempts: Mapped[int] = mapped_column(Integer)
    max_input_tokens: Mapped[int] = mapped_column(Integer)
    max_output_tokens: Mapped[int] = mapped_column(Integer)
    max_retrieval_http: Mapped[int] = mapped_column(Integer)
    max_total_http: Mapped[int] = mapped_column(Integer)
    max_tool_calls: Mapped[int] = mapped_column(Integer)
    max_active_seconds: Mapped[int] = mapped_column(Integer)
    max_model_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_other_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_model_attempts: Mapped[int] = mapped_column(Integer, default=0)
    settled_model_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    settled_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reserved_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    settled_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reserved_retrieval_http: Mapped[int] = mapped_column(Integer, default=0)
    settled_retrieval_http: Mapped[int] = mapped_column(Integer, default=0)
    reserved_total_http: Mapped[int] = mapped_column(Integer, default=0)
    settled_total_http: Mapped[int] = mapped_column(Integer, default=0)
    reserved_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    settled_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    reserved_model_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    settled_model_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_other_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    settled_other_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    settled_active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class AgentBudgetReservationRecord(Base):
    __tablename__ = "agent_budget_reservations"
    __table_args__ = (
        UniqueConstraint("step_id", "attempt"),
        CheckConstraint("attempt >= 1", name="ck_budget_reservation_attempt_positive"),
        CheckConstraint(
            "status IN ('active', 'settled', 'released')",
            name="ck_budget_reservation_status",
        ),
    ) + tuple(
        CheckConstraint(
            f"reserved_{name} >= 0 AND actual_{name} >= 0 "
            f"AND actual_{name} <= reserved_{name}",
            name=f"ck_budget_reservation_{name}_bounds",
        )
        for name in (
            "model_attempts",
            "input_tokens",
            "output_tokens",
            "retrieval_http",
            "total_http",
            "tool_calls",
            "model_http_attempts",
            "other_http_attempts",
            "active_seconds",
        )
    ) + (
        CheckConstraint(
            "reserved_total_http = reserved_retrieval_http + "
            "reserved_model_http_attempts + reserved_other_http_attempts",
            name="ck_budget_reservation_reserved_http_conservation",
        ),
        CheckConstraint(
            "actual_total_http = actual_retrieval_http + "
            "actual_model_http_attempts + actual_other_http_attempts",
            name="ck_budget_reservation_actual_http_conservation",
        ),
    )

    reservation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    budget_id: Mapped[str] = mapped_column(String(64), index=True)
    child_run_id: Mapped[str] = mapped_column(String(64), index=True)
    step_id: Mapped[str] = mapped_column(String(64), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(128))
    reserved_model_attempts: Mapped[int] = mapped_column(Integer, default=0)
    actual_model_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    actual_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reserved_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    actual_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reserved_retrieval_http: Mapped[int] = mapped_column(Integer, default=0)
    actual_retrieval_http: Mapped[int] = mapped_column(Integer, default=0)
    reserved_total_http: Mapped[int] = mapped_column(Integer, default=0)
    actual_total_http: Mapped[int] = mapped_column(Integer, default=0)
    reserved_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    actual_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    reserved_model_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    actual_model_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_other_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    actual_other_http_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reserved_active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    actual_active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
