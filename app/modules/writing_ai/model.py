"""Persistence model for unconfirmed AI writing suggestions."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WritingAiSuggestion(Base):
    __tablename__ = "writing_ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"), index=True
    )
    task: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_mappings_json: Mapped[str] = mapped_column(Text, nullable=False)
    requires_human_confirmation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adopted_version: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
