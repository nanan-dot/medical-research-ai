"""A1 membership is derived; shared A0 source identity remains immutable."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentAnchorSegment(Base):
    __tablename__ = "document_anchor_segments"
    __table_args__ = (
        UniqueConstraint(
            "anchor_id",
            "segmentation_revision_id",
            "coverage_order",
            name="uq_anchor_coverage",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="CASCADE"), index=True
    )
    segmentation_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE")
    )
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("document_layout_segments.id", ondelete="CASCADE")
    )
    coverage_order: Mapped[int]
    segment_char_start: Mapped[int]
    segment_char_end: Mapped[int]
    coverage_type: Mapped[str] = mapped_column(String(16))


class DocumentReadingNote(Base):
    __tablename__ = "document_reading_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id")
    )
    content: Mapped[str] = mapped_column(Text)
    quote_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class SelectionOperation(Base):
    __tablename__ = "document_selection_operations"
    __table_args__ = (
        UniqueConstraint(
            "scope", "operation", "idempotency_key", name="uq_selection_operation"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)
