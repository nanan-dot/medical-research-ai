"""Persistence model for simulated writing-project reviews."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WritingReview(Base):
    __tablename__ = "writing_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"), index=True
    )
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewer_label: Mapped[str] = mapped_column(String(100), nullable=False)
    findings_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
