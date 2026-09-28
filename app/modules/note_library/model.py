"""Persistence model for versioned notes and their organization relationships."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchNote(Base):
    __tablename__ = "research_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_scope: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
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


class NoteDraft(Base):
    __tablename__ = "note_drafts"
    __table_args__ = (
        UniqueConstraint("note_id", "actor_scope", name="uq_note_draft_actor"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    save_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft_saved"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class NoteRevision(Base):
    __tablename__ = "note_revisions"
    __table_args__ = (
        UniqueConstraint("note_id", "revision_no", name="uq_note_revision_no"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    restored_from_revision: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class NoteSourceLink(Base):
    __tablename__ = "note_source_links"
    __table_args__ = (Index("ix_note_source_revision", "revision_id", "source_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("note_revisions.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    source_version: Mapped[str | None] = mapped_column(String(128))
    document_id: Mapped[int | None] = mapped_column(Integer)
    anchor_id: Mapped[int | None] = mapped_column(Integer)
    granularity: Mapped[str] = mapped_column(String(24), nullable=False)
    title_snapshot: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    quote_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url_snapshot: Mapped[str | None] = mapped_column(Text)
    created_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="accessible"
    )


class NoteResearchLink(Base):
    __tablename__ = "note_research_links"
    __table_args__ = (
        UniqueConstraint(
            "note_id", "research_context_id", name="uq_note_research_link"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    research_context_id: Mapped[int] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class NoteTag(Base):
    __tablename__ = "note_tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    normalized_name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)


class NoteTagLink(Base):
    __tablename__ = "note_tag_links"
    __table_args__ = (UniqueConstraint("note_id", "tag_id", name="uq_note_tag_link"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("note_tags.id", ondelete="CASCADE"), nullable=False, index=True
    )


class NoteActivity(Base):
    __tablename__ = "note_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class NoteSaveOperation(Base):
    __tablename__ = "note_save_operations"
    __table_args__ = (
        UniqueConstraint(
            "actor_scope", "note_id", "idempotency_key", name="uq_note_save_operation"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("note_revisions.id", ondelete="CASCADE"), nullable=False
    )


class NoteAISuggestion(Base):
    __tablename__ = "note_ai_suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_revision: Mapped[int | None] = mapped_column(Integer)
    input_draft_version: Mapped[int | None] = mapped_column(Integer)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    output_title: Mapped[str | None] = mapped_column(String(200))
    output_body: Mapped[str | None] = mapped_column(Text)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class NoteDerivation(Base):
    __tablename__ = "note_derivations"
    __table_args__ = (
        UniqueConstraint(
            "actor_scope", "idempotency_key", name="uq_note_derivation_key"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False
    )
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("note_revisions.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate")


class NoteLegacyBackfill(Base):
    __tablename__ = "note_legacy_backfills"
    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("research_notes.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
