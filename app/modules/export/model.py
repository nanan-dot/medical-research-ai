from datetime import datetime
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ExportRecord(Base):
    __tablename__ = "exports"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    export_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ids: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_info: Mapped[str | None] = mapped_column(Text)
    pending_confirmations: Mapped[str | None] = mapped_column(Text)
    local_output_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
