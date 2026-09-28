"""Knowledge-source persistence model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        Index(
            "ix_knowledge_sources_auto_sync_due",
            "auto_sync",
            "enabled",
            "next_auto_sync_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_sync: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    next_auto_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_auto_sync_enqueued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    auto_sync_failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_opened_by: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    sync_added: Mapped[int] = mapped_column(default=0, nullable=False)
    sync_modified: Mapped[int] = mapped_column(default=0, nullable=False)
    sync_deleted: Mapped[int] = mapped_column(default=0, nullable=False)
    sync_skipped: Mapped[int] = mapped_column(default=0, nullable=False)
    sync_failed: Mapped[int] = mapped_column(default=0, nullable=False)
