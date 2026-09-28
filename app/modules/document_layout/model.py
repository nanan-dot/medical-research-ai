"""Immutable A1 derived layout records; A0 TextItems are never updated."""

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


class DocumentSegmentationRevision(Base):
    __tablename__ = "document_segmentation_revisions"
    __table_args__ = (
        Index(
            "uq_segmentation_current_anchor",
            "anchor_revision_id",
            unique=True,
            sqlite_where=text("state IN ('ready', 'review_required')"),
            postgresql_where=text("state IN ('ready', 'review_required')"),
        ),
        UniqueConstraint(
            "anchor_revision_id", "request_fingerprint", name="uq_segmentation_request"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    anchor_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"), index=True
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    segmentation_fingerprint: Mapped[str | None] = mapped_column(String(64))
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quality_summary_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentLayoutBlock(Base):
    __tablename__ = "document_layout_blocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    segmentation_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_pages.id", ondelete="CASCADE"), index=True
    )
    block_order: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    item_indexes_json: Mapped[str] = mapped_column(Text, nullable=False)
    bbox_json: Mapped[str] = mapped_column(Text, nullable=False)
    quality_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class DocumentLayoutSection(Base):
    __tablename__ = "document_layout_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    segmentation_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"), index=True
    )
    literal_title: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_role: Mapped[str | None] = mapped_column(String(32))
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    first_page: Mapped[int] = mapped_column(Integer, nullable=False)
    last_page: Mapped[int] = mapped_column(Integer, nullable=False)


class DocumentLayoutSegment(Base):
    __tablename__ = "document_layout_segments"
    __table_args__ = (
        UniqueConstraint(
            "segmentation_revision_id", "reading_order", name="uq_layout_segment_order"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    segmentation_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"), index=True
    )
    segment_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    section_path_json: Mapped[str] = mapped_column(Text, nullable=False)
    translation_eligibility: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    first_page: Mapped[int] = mapped_column(Integer, nullable=False)
    last_page: Mapped[int] = mapped_column(Integer, nullable=False)


class DocumentLayoutFragment(Base):
    __tablename__ = "document_layout_fragments"
    __table_args__ = (
        UniqueConstraint(
            "segment_id", "fragment_order", name="uq_layout_fragment_order"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("document_layout_segments.id", ondelete="CASCADE"), index=True
    )
    fragment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_pages.id", ondelete="CASCADE"), index=True
    )
    start_item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_item_index: Mapped[int] = mapped_column(Integer, nullable=False)
