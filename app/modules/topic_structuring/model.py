"""Persistent immutable snapshots for structured research topics."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TopicStructuring(Base):
    """Stable identity that preserves the user's original topic verbatim."""

    __tablename__ = "topic_structurings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original_topic: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TopicStructuringVersion(Base):
    """One editable-result snapshot; old snapshots are never overwritten."""

    __tablename__ = "topic_structuring_versions"
    __table_args__ = (
        UniqueConstraint(
            "topic_structuring_id", "version", name="uq_topic_structuring_versions"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic_structuring_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topic_structurings.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    structured_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
