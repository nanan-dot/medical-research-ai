"""事务 Outbox。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentOutboxRecord(Base):
    __tablename__ = "agent_outbox"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('run.created','run.status_changed','step.status_changed',"
            "'artifact.created','artifact.invalidated','confirmation.requested',"
            "'confirmation.recorded','confirmation.superseded','budget.reserved',"
            "'budget.settled','export.prepared','export.completed','error.raised')",
            name="ck_agent_outbox_public_type",
        ),
        CheckConstraint(
            "attempt_count >= 0", name="ck_agent_outbox_attempt_nonnegative"
        ),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
