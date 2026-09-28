"""Persistence models owned by the research-resource library."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentAccess(Base):
    """One durable, throttled recent-access aggregate per document."""

    __tablename__ = "document_accesses"
    __table_args__ = (Index("ix_document_accesses_last_opened", "last_opened_at", "document_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    last_opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_opened_by: Mapped[str | None] = mapped_column(String(128))
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_open_request_key: Mapped[str | None] = mapped_column(String(128))


class ZoteroLibrary(Base):
    """Non-secret identity and incremental state for one Zotero source."""

    __tablename__ = "zotero_libraries"
    __table_args__ = (
        UniqueConstraint("library_type", "library_id", name="uq_zotero_library_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    library_type: Mapped[str] = mapped_column(String(16), nullable=False)
    library_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_cursor: Mapped[str | None] = mapped_column(String(64))
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ZoteroCollection(Base):
    """Cached collection tree so browsing does not require remote I/O."""

    __tablename__ = "zotero_collections"
    __table_args__ = (
        UniqueConstraint("zotero_library_id", "collection_key", name="uq_zotero_collection_key"),
        Index("ix_zotero_collections_parent", "zotero_library_id", "parent_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    zotero_library_id: Mapped[int] = mapped_column(
        ForeignKey("zotero_libraries.id", ondelete="CASCADE"), nullable=False
    )
    collection_key: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_key: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64))
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
