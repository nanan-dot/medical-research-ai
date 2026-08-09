from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Presentation(Base):
    __tablename__ = "presentations"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    outline_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
