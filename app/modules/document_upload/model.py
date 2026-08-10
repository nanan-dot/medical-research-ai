"""文档原始资产持久化模型。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.document.model import Document


class DocumentAsset(Base):
    """保存可追溯的原始文件资产，不复用知识源目录语义。"""

    __tablename__ = "document_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    asset_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_relative_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_parse",
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    document: Mapped[Document] = relationship("Document", back_populates="asset")
