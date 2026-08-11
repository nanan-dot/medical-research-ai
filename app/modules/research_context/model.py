"""Persistent research contexts and their authorized local documents."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchContext(Base):
    __tablename__ = "research_contexts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class ResearchContextDocument(Base):
    __tablename__ = "research_context_documents"
    __table_args__ = (
        UniqueConstraint("research_context_id", "document_id", name="uq_research_context_document"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_context_id: Mapped[int] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
