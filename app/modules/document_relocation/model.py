"""Additive A3 records; original evidence is never overwritten by relocation."""

from datetime import datetime

from sqlalchemy import (
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


class DocumentFileRevision(Base):
    __tablename__ = "document_file_revisions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "file_hash", name="uq_document_file_revision_hash"
        ),
        Index(
            "uq_document_file_revision_current",
            "document_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current = true"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    file_hash: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer)
    modified_time_ns: Mapped[int | None] = mapped_column()
    storage_kind: Mapped[str] = mapped_column(String(32), default="external")
    storage_reference: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(default=False, index=True)
    is_content_available: Mapped[bool] = mapped_column(default=False)
    retention_status: Mapped[str] = mapped_column(String(32), default="metadata_only")
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentAnchorRelocation(Base):
    __tablename__ = "document_anchor_relocations"
    __table_args__ = (
        UniqueConstraint(
            "source_anchor_id",
            "target_anchor_revision_id",
            "candidate_anchor_id",
            "algorithm_version",
            name="uq_anchor_relocation_candidate",
        ),
        Index(
            "ix_anchor_relocation_source_target",
            "source_anchor_id",
            "target_anchor_revision_id",
        ),
        Index(
            "uq_anchor_relocation_confirmed",
            "source_anchor_id",
            "target_anchor_revision_id",
            unique=True,
            sqlite_where=text("status = 'confirmed'"),
            postgresql_where=text("status = 'confirmed'"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="CASCADE"), index=True
    )
    target_anchor_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"), index=True
    )
    candidate_anchor_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="SET NULL")
    )
    method: Mapped[str] = mapped_column(String(32))
    algorithm_version: Mapped[str] = mapped_column(String(64))
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    protected_token_status: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="proposed", index=True)
    decision_source: Mapped[str | None] = mapped_column(String(32))
    reviewer_id: Mapped[str | None] = mapped_column(String(128))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class AssetAnchorLink(Base):
    __tablename__ = "asset_anchor_links"
    __table_args__ = (
        UniqueConstraint("asset_type", "asset_id", name="uq_asset_anchor_link"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(64))
    asset_id: Mapped[int] = mapped_column(Integer)
    original_anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True
    )
    resolved_anchor_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="SET NULL"), index=True
    )
    resolution_status: Mapped[str] = mapped_column(String(32), default="anchored_exact")
    resolution_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class DocumentAnchorRelocationDecision(Base):
    __tablename__ = "document_anchor_relocation_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    relocation_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_relocations.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(32))
    decision_source: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[str] = mapped_column(String(128))
    decision_note: Mapped[str | None] = mapped_column(Text)
    previous_resolution_version: Mapped[int] = mapped_column(Integer)
    resulting_resolution_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class LegacyAnchorBackfillRun(Base):
    __tablename__ = "legacy_anchor_backfill_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_records.id", ondelete="SET NULL"), index=True
    )
    asset_type: Mapped[str] = mapped_column(String(64))
    source_schema_version: Mapped[str] = mapped_column(String(64))
    target_anchor_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(String(16))
    cursor: Mapped[str | None] = mapped_column(String(128))
    total: Mapped[int] = mapped_column(Integer, default=0)
    scanned: Mapped[int] = mapped_column(Integer, default=0)
    exact: Mapped[int] = mapped_column(Integer, default=0)
    candidate: Mapped[int] = mapped_column(Integer, default=0)
    unresolved: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    algorithm_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegacyAnchorBackfillItem(Base):
    __tablename__ = "legacy_anchor_backfill_items"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "asset_type", "asset_id", name="uq_anchor_backfill_item"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("legacy_anchor_backfill_runs.id", ondelete="CASCADE"), index=True
    )
    asset_type: Mapped[str] = mapped_column(String(64))
    asset_id: Mapped[int] = mapped_column(Integer)
    legacy_identity_hash: Mapped[str] = mapped_column(String(64))
    result_status: Mapped[str] = mapped_column(String(32))
    anchor_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="SET NULL")
    )
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    reason_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    error_code: Mapped[str | None] = mapped_column(String(64))
