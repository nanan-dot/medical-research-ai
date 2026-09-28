"""SQLAlchemy persistence for versioned reading plans."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReadingPlan(Base):
    __tablename__ = "reading_plans"
    __table_args__ = (
        UniqueConstraint("result_id", "version", name="uq_reading_plan_result_version"),
        Index("ix_reading_plan_active", "result_id", "status"),
        Index("uq_reading_plan_one_active", "result_id", unique=True, sqlite_where=text("status = 'active'"), postgresql_where=text("status = 'active'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("literature_search_results.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    generation_basis_json: Mapped[str] = mapped_column(Text, nullable=False)
    duplicate_mode: Mapped[str] = mapped_column(Text, nullable=False, default="all")
    target_core_count: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items: Mapped[list["ReadingPlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", lazy="selectin"
    )


class ReadingPlanItem(Base):
    __tablename__ = "reading_plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "pmid", name="uq_reading_plan_item_plan_pmid"),
        Index("ix_reading_plan_item_stage_role", "plan_id", "stage", "role", "stage_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("reading_plans.id", ondelete="CASCADE"), nullable=False
    )
    pmid: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    reading_reason_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_features_json: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    is_locked: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    plan: Mapped[ReadingPlan] = relationship(back_populates="items")
