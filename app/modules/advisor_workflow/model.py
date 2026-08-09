"""Persistence entities for user-recorded advisor workflow state."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdvisorReview(Base):
    __tablename__ = "advisor_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    direction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_directions.id"), index=True
    )
    reviewer_type: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    points_json: Mapped[str] = mapped_column(Text, nullable=False)
    literature_gaps_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    experiment_conditions_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class DirectionRevision(Base):
    __tablename__ = "direction_revisions"
    __table_args__ = (
        UniqueConstraint(
            "direction_id", "version", name="uq_direction_revision_version"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    direction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_directions.id"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("direction_revisions.id")
    )
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
