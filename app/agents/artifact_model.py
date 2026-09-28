"""M0 正式产物、依赖和失效记录。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentArtifactRecord(Base):
    __tablename__ = "agent_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "research_context_id", "artifact_type", "artifact_key", "version_key"
        ),
        CheckConstraint(
            "validity_status IN ('valid','needs_revalidation','stale','superseded','invalid')",
            name="ck_agent_artifact_validity_status",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(96), index=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    artifact_key: Mapped[str] = mapped_column(String(128))
    version_key: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(32))
    registry_version: Mapped[str] = mapped_column(String(64))
    validity_status: Mapped[str] = mapped_column(String(32), index=True)
    typed_ref_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ArtifactDependencyRecord(Base):
    __tablename__ = "artifact_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "downstream_artifact_id", "upstream_artifact_id", "upstream_version_key"
        ),
    )

    dependency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    downstream_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("agent_artifacts.artifact_id", ondelete="CASCADE"), index=True
    )
    upstream_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("agent_artifacts.artifact_id", ondelete="CASCADE"), index=True
    )
    upstream_version_key: Mapped[str] = mapped_column(String(128))
    upstream_content_hash: Mapped[str] = mapped_column(String(64))
    dependency_kind: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvalidationRecord(Base):
    __tablename__ = "invalidation_records"

    invalidation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_artifact_id: Mapped[str] = mapped_column(String(64), index=True)
    upstream_artifact_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    reason_code: Mapped[str] = mapped_column(String(128))
    old_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
