from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"
    __table_args__ = (
        Index(
            "uq_model_configs_default",
            "is_default",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deployment_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    api_base: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_cloud_content: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
