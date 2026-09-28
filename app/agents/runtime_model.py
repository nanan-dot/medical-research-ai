"""M0 运行时结构化持久化模型。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentTaskRequestRecord(Base):
    __tablename__ = "agent_task_requests"
    __table_args__ = (
        CheckConstraint(
            "requested_agent IN ('A1','A2','A3','A4','A5')",
            name="ck_agent_task_requested_agent",
        ),
    )

    task_request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    requested_agent: Mapped[str] = mapped_column(String(32))
    intent: Mapped[str] = mapped_column(String(128))
    input_artifact_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    authorization_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentStepRecord(Base):
    __tablename__ = "agent_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "step_kind", "attempt"),
        CheckConstraint(
            "status IN ('created','running','awaiting_user_input',"
            "'awaiting_confirmation','completed','failed','cancelled','skipped')",
            name="ck_agent_step_public_status",
        ),
        CheckConstraint("attempt >= 1", name="ck_agent_step_attempt_positive"),
        CheckConstraint("revision >= 1", name="ck_agent_step_revision_positive"),
    )

    step_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"), index=True
    )
    step_kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_refs_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list
    )
    expected_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class AgentEventRecord(Base):
    __tablename__ = "agent_events"
    __table_args__ = (
        UniqueConstraint("run_id", "seq"),
        CheckConstraint(
            "event_type IN ('run.created','run.status_changed','step.status_changed',"
            "'artifact.created','artifact.invalidated','confirmation.requested',"
            "'confirmation.recorded','confirmation.superseded','budget.reserved',"
            "'budget.settled','export.prepared','export.completed','error.raised')",
            name="ck_agent_event_public_type",
        ),
        CheckConstraint("seq >= 1", name="ck_agent_event_seq_positive"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    detail_kind: Mapped[str] = mapped_column(String(64))
    detail_json: Mapped[dict[str, object]] = mapped_column(JSON)
    artifact_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentExternalExecutionRecord(Base):
    """Server-owned ledger for the send/commit recovery boundary."""

    __tablename__ = "agent_external_executions"
    __table_args__ = (
        UniqueConstraint("step_id", "attempt"),
        UniqueConstraint("run_id", "execution_seq", name="uq_execution_run_seq"),
        CheckConstraint("execution_seq >= 1", name="ck_execution_seq_positive"),
        CheckConstraint(
            "state IN ('prepared','sent','succeeded','failed_before_send','outcome_unknown')",
            name="ck_agent_external_execution_state",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_external_execution_revision_positive"
        ),
    )

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    execution_seq: Mapped[int] = mapped_column(Integer)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    step_id: Mapped[str] = mapped_column(String(64), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    request_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authorization_id: Mapped[str] = mapped_column(String(64))
    reservation_id: Mapped[str] = mapped_column(String(64))
    expected_artifact_type: Mapped[str | None] = mapped_column(String(96), nullable=True)
    expected_artifact_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formal_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    result_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
