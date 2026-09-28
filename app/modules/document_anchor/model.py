"""Persistent immutable A0 document anchor revisions and TextItems."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class DocumentAnchorRevision(Base):
    """A complete, versioned PDF.js text-layer extraction for one document file."""

    __tablename__ = "document_anchor_revisions"
    __table_args__ = (
        Index(
            "uq_anchor_current_document",
            "document_id",
            unique=True,
            sqlite_where=text("state IN ('ready', 'review_required')"),
            postgresql_where=text("state IN ('ready', 'review_required')"),
        ),
        UniqueConstraint(
            "document_id", "request_fingerprint", name="uq_anchor_revision_request"
        ),
        UniqueConstraint(
            "document_id",
            "file_hash",
            "extraction_fingerprint",
            name="uq_anchor_revision_complete",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_file_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_file_revisions.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_fingerprint: Mapped[str | None] = mapped_column(String(64))
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    pdfjs_version: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(64), nullable=False)
    options_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quality_summary_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentSourcePage(Base):
    """One physical PDF page; raw and derived text are intentionally separate."""

    __tablename__ = "document_source_pages"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "page_number", name="uq_source_page_revision_number"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False)
    view_box_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    styles_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    quality_metrics_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    char_map_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class DocumentSourceTextItem(Base):
    """The shared stable PDF.js TextItem identity within one physical page."""

    __tablename__ = "document_source_text_items"
    __table_args__ = (
        UniqueConstraint(
            "page_id", "item_index", name="uq_source_text_item_page_index"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_array_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    transform_json: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    has_eol: Mapped[bool] = mapped_column(Boolean, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    font_name: Mapped[str | None] = mapped_column(String(256))
    normalized_char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_utf16_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_map_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    bbox_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class DocumentSourceAnchor(Base):
    """Immutable, server-reconstructed A2 reference to one A0 revision."""

    __tablename__ = "document_source_anchors"
    __table_args__ = (
        UniqueConstraint("content_fingerprint", name="uq_source_anchor_content"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    anchor_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"), index=True
    )
    anchor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_quote: Mapped[str] = mapped_column(Text, nullable=False)
    quote_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suffix: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quality_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="review_required"
    )
    join_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="a2-space-nfc-1"
    )
    resolution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="exact"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class DocumentAnchorFragment(Base):
    __tablename__ = "document_anchor_fragments"
    __table_args__ = (
        UniqueConstraint(
            "anchor_id", "fragment_order", name="uq_anchor_fragment_order"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="CASCADE"), index=True
    )
    fragment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_pages.id", ondelete="CASCADE"), nullable=False
    )
    start_item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset_utf16: Mapped[int] = mapped_column(Integer, nullable=False)
    end_item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset_utf16: Mapped[int] = mapped_column(Integer, nullable=False)
    rectangles_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reconstructed_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
