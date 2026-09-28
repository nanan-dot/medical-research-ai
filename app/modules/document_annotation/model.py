"""与固定文档版本绑定的 PDF 文本批注模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentAnnotation(Base):
    """保存本地研究者的批注，不引入不存在的协作者或用户身份。"""

    __tablename__ = "document_annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_anchor_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_source_anchors.id"), nullable=True, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_geometry: Mapped[str] = mapped_column(Text, nullable=False)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    selected_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
