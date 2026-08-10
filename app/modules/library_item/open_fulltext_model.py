"""Persistence for a traceable official-PMC full-text acquisition attempt."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OpenFulltextAcquisition(Base):
    """Keep the legal verification outcome even when no file can be retrieved.

    Every official request gets an immutable audit row, so a later failure cannot
    overwrite the provenance of an earlier verified local PDF.
    """

    __tablename__ = "fulltext_retrievals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    pmcid: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(255))
    file_format: Mapped[str | None] = mapped_column(String(24))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
