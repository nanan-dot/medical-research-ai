"""Persisted structured single-paper analyses."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaperAnalysis(Base):
    __tablename__ = "paper_analysiss"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(nullable=False, default=1)
    structured_result: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[str | None] = mapped_column(Text)
    pending_confirmations: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
