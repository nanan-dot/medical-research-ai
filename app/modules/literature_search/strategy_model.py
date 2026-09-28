"""Persistent working strategies, deliberately separate from search-result snapshots."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SearchStrategyDraft(Base):
    """Mutable, revision-protected strategy users are currently editing."""

    __tablename__ = "search_strategy_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    intent_mode: Mapped[str] = mapped_column(Text, nullable=False, default="unstructured")
    intent_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    limits_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    query_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    query_source: Mapped[str] = mapped_column(Text, nullable=False, default="generated")
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generation_state: Mapped[str] = mapped_column(Text, nullable=False, default="ready")
    validation_state: Mapped[str] = mapped_column(Text, nullable=False, default="stale")
    count_state: Mapped[str] = mapped_column(Text, nullable=False, default="stale")
    count_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"), onupdate=sql_text("CURRENT_TIMESTAMP"))
    last_saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))


class SearchStrategyTerm(Base):
    """One editable, source-labelled search term in a working draft."""

    __tablename__ = "search_strategy_terms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_group: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    field_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    relation_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_locked: Mapped[bool] = mapped_column(nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"), onupdate=sql_text("CURRENT_TIMESTAMP"))


class SearchStrategyMeshTerm(Base):
    """NLM-provided MeSH evidence; verification status is never inferred by UI."""

    __tablename__ = "search_strategy_mesh_terms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    descriptor: Mapped[str] = mapped_column(Text, nullable=False)
    mesh_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept_group: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="nlm_mesh")
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="stale")
    is_locked: Mapped[bool] = mapped_column(nullable=False, default=False)
    verification_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SearchStrategyVersion(Base):
    """Immutable strategy snapshot; it is not a LiteratureSearch result version."""

    __tablename__ = "search_strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_search_strategy_version"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
