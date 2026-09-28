"""公共幂等记录。"""

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentIdempotencyRecord(Base):
    __tablename__ = "agent_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "research_context_id", "actor_scope", "action", "idempotency_key"
        ),
    )

    idempotency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_scope: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    resource_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
