from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_completion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    useful: Mapped[bool | None] = mapped_column(Boolean)
    citation_correct: Mapped[bool | None] = mapped_column(Boolean)
    data_correct: Mapped[bool | None] = mapped_column(Boolean)
    error_type: Mapped[str | None] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    next_step: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
