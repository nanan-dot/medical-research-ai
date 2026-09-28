"""人工确认和专业角色决定模型。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchContextMembershipRecord(Base):
    __tablename__ = "research_context_memberships"
    __table_args__ = (UniqueConstraint("research_context_id", "actor_scope"),)

    membership_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_scope: Mapped[str] = mapped_column(String(128))
    membership_role: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentRoleQualificationRecord(Base):
    __tablename__ = "agent_role_qualifications"

    qualification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    authorized_role: Mapped[str] = mapped_column(String(64))
    source_kind: Mapped[str] = mapped_column(String(64))
    source_ref: Mapped[str] = mapped_column(String(256))
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32))
    revision: Mapped[int] = mapped_column(Integer, default=1)


class UserConfirmationRecord(Base):
    __tablename__ = "user_confirmations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','consumed','rejected','cancelled','expired','superseded')",
            name="ck_user_confirmation_status",
        ),
        CheckConstraint("revision >= 1", name="ck_user_confirmation_revision_positive"),
    )

    confirmation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_scope: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(64))
    target_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    binding_hash: Mapped[str] = mapped_column(String(64), index=True)
    expected_revisions_json: Mapped[dict[str, int]] = mapped_column(JSON)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class RoleDecisionRecord(Base):
    __tablename__ = "role_decisions"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_id: Mapped[str] = mapped_column(String(64), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    confirmation_id: Mapped[str] = mapped_column(String(64))
    actor_scope: Mapped[str] = mapped_column(String(128))
    authorized_role: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    target_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    target_binding_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
