from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Outline(Base):
    __tablename__ = "outlines"
    id: Mapped[int] = mapped_column(primary_key=True)
    matrix_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    claims_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    based_on_matrix_version: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    document_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_by_user: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
