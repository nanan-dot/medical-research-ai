"""Persistence entities for evidence-backed comparison matrices."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ComparisonTask(Base):
    __tablename__ = "comparison_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    selected_document_ids: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ComparisonCell(Base):
    __tablename__ = "comparison_cells"
    __table_args__ = (
        UniqueConstraint(
            "comparison_id", "document_id", "field", name="uq_comparison_cell"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    comparison_id: Mapped[int] = mapped_column(
        ForeignKey("comparison_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    cell_value: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    generated_value: Mapped[str | None] = mapped_column(Text)
    user_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
