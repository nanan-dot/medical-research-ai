"""Persistence models for feasibility score snapshots and weight profiles."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FeasibilityScore(Base):
    """An immutable, versioned feasibility score for one research direction."""

    __tablename__ = "feasibility_scores"
    __table_args__ = (
        UniqueConstraint(
            "direction_id",
            "version",
            name="uq_feasibility_score_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    direction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("research_directions.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions_json: Mapped[str] = mapped_column(Text, nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    total_score: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    missing_inputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    ranking_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class FeasibilityWeightProfile(Base):
    """An auditable named set of feasibility dimension weights."""

    __tablename__ = "feasibility_weight_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
