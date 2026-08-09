"""Persistence model for a formal local-library record."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LibraryItem(Base):
    """A formal collection differs from the transient search-result saved flag.

    `literature_search_item_state.saved` is a per-result working marker. This table is
    the durable local-library record and retains the source search result for traceability.
    """

    __tablename__ = "library_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pmid: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    doi: Mapped[str | None] = mapped_column(
        Text, nullable=True, unique=True, index=True
    )
    title: Mapped[str | None] = mapped_column(Text)
    journal: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    source_search_id: Mapped[int] = mapped_column(
        ForeignKey("literature_search_results.id"), nullable=False
    )
    fulltext_status: Mapped[str] = mapped_column(Text, nullable=False)
    fulltext_status_reason: Mapped[str] = mapped_column(Text, nullable=False)
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
