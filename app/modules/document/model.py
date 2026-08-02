"""Files tracked inside an authorized knowledge source."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_source_id", "normalized_file_path", name="uq_documents_source_path"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_time_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scan_state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    index_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
