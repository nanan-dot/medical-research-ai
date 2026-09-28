"""Agent 运行的最小应用层持久化模型。"""

from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentRunRecord(Base):
    """保存可恢复状态、审批决定与脱敏轨迹，不保存查询或证据正文。"""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "workflow_status IN ('created','running','awaiting_user_input',"
            "'awaiting_confirmation','recovery_required','completed','partial',"
            "'failed','rejected','cancelled','cancelled_after_commit')",
            name="ck_agent_run_public_status",
        ),
        CheckConstraint(
            "is_legacy OR (research_context_id IS NOT NULL AND task_request_id IS NOT NULL "
            "AND agent_type IN ('A1','A2','A3','A4','A5') "
            "AND run_mode IN ('standalone_confirmation','composite_workflow'))",
            name="ck_agent_run_structured_identity",
        ),
        CheckConstraint("revision >= 1", name="ck_agent_run_revision_positive"),
    )

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_status: Mapped[str] = mapped_column(String(32), index=True)
    state_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    events_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    retrieval_trace_json: Mapped[dict[str, object] | None] = mapped_column(
        JSON, nullable=True
    )
    research_context_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    task_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    root_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    parent_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    agent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    run_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phase: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_legacy: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
