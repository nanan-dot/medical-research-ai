"""Files tracked inside an authorized knowledge source."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# DocumentAsset 定义在 document_upload 模块；repository.py 已有同样导入，
# 模块间为单向依赖（document → document_upload），无循环风险。
from app.modules.document_upload.model import DocumentAsset


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_source_id",
            "normalized_file_path",
            name="uq_documents_source_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    modified_time_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scan_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    parse_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    index_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parsed_title: Mapped[str | None] = mapped_column(String(500))
    parsed_content: Mapped[str | None] = mapped_column(Text)
    parsed_is_scanned: Mapped[bool | None]
    parsed_page_count: Mapped[int | None]
    paperqa_index_key: Mapped[str | None] = mapped_column(String(128))
    paperqa_version: Mapped[str | None] = mapped_column(String(64))
    indexed_hash: Mapped[str | None] = mapped_column(String(64))
    index_error: Mapped[str | None] = mapped_column(Text)
    asset: Mapped["DocumentAsset | None"] = relationship(
        "DocumentAsset",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def original_filename(self) -> str | None:
        """Expose the user-facing name without treating it as a storage path."""
        return self.asset.original_filename if self.asset is not None else None

    @property
    def media_type(self) -> str | None:
        """Expose the verified media type when this document has a managed asset."""
        return self.asset.media_type if self.asset is not None else None
