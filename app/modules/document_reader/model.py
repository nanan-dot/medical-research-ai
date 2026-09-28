"""论文阅读工作区持久化模型。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
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


class ReaderSession(Base):
    __tablename__ = "reader_sessions"
    __table_args__ = (
        Index("uq_reader_session_idempotency", "actor_scope", "idempotency_key", unique=True),
        CheckConstraint("last_page >= 1", name="ck_reader_session_page"),
        CheckConstraint("viewport_offset_ratio >= 0 AND viewport_offset_ratio <= 1", name="ck_reader_session_offset"),
        Index("ix_reader_session_history", "actor_scope", "last_seen_at", "id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    library_item_id: Mapped[int] = mapped_column(ForeignKey("library_items.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    document_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_revision_id: Mapped[int | None] = mapped_column(ForeignKey("document_anchor_revisions.id", ondelete="SET NULL"))
    segmentation_revision_id: Mapped[int | None] = mapped_column(ForeignKey("document_segmentation_revisions.id", ondelete="SET NULL"))
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    idempotency_payload_hash: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_page: Mapped[int] = mapped_column(Integer, default=1)
    last_anchor_id: Mapped[int | None] = mapped_column(ForeignKey("document_source_anchors.id", ondelete="SET NULL"))
    viewport_offset_ratio: Mapped[float] = mapped_column(Float, default=0)
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    close_reason: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    is_history_hidden: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ReaderPageExposure(Base):
    __tablename__ = "reader_page_exposures"
    __table_args__ = (UniqueConstraint("session_id", "page_number", name="uq_reader_exposure_page"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("reader_sessions.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    first_visible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_visible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    visible_milliseconds: Mapped[int] = mapped_column(Integer, default=0)
    max_visible_ratio: Mapped[float] = mapped_column(Float, default=0)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ReaderPreference(Base):
    __tablename__ = "reader_preferences"
    __table_args__ = (UniqueConstraint("actor_scope", "document_id", name="uq_reader_preference_scope_document"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    view_mode: Mapped[str] = mapped_column(String(16), default="original")
    zoom_percent: Mapped[int] = mapped_column(Integer, default=100)
    left_panel_mode: Mapped[str] = mapped_column(String(32), default="outline")
    left_collapsed: Mapped[bool] = mapped_column(default=False)
    right_panel_tab: Mapped[str] = mapped_column(String(32), default="copilot")
    focus_mode: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class ReaderBookmark(Base):
    __tablename__ = "reader_bookmarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    source_anchor_id: Mapped[int] = mapped_column(ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True)
    label: Mapped[str | None] = mapped_column(String(200))
    color: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ReaderQuestion(Base):
    __tablename__ = "reader_questions"
    __table_args__ = (CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_reader_question_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    source_anchor_id: Mapped[int] = mapped_column(ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    linked_conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"))
    linked_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ResearchMaterialCandidate(Base):
    __tablename__ = "research_material_candidates"
    __table_args__ = (
        UniqueConstraint("actor_scope", "idempotency_key", name="uq_research_candidate_idempotency"),
        CheckConstraint("status IN ('candidate','accepted','rejected')", name="ck_research_candidate_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    research_context_id: Mapped[int] = mapped_column(ForeignKey("research_contexts.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    source_anchor_id: Mapped[int] = mapped_column(ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True)
    candidate_type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(String(300))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="candidate")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    idempotency_payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class PaperReaderState(Base):
    __tablename__ = "paper_reader_states"
    __table_args__ = (
        UniqueConstraint(
            "actor_scope", "library_item_id", name="uq_reader_state_scope_item"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), index=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE")
    )
    is_favorite: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class ReaderIdempotencyRecord(Base):
    """为没有专属幂等字段的交接动作保存稳定结果身份。"""

    __tablename__ = "reader_idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_scope", "action", "idempotency_key", name="uq_reader_idempotency_action_key"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
