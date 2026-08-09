"""研究条件及其不可变版本快照的数据模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchConditions(Base):
    """研究条件的稳定标识及当前版本指针。"""

    __tablename__ = "research_conditions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    current_version: Mapped[int] = mapped_column(nullable=False, default=1)
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


class ResearchConditionsVersion(Base):
    """条件快照；JSON 逐字段保留 known/source，禁止在持久化层推测用户信息。"""

    __tablename__ = "research_conditions_versions"
    # (conditions_id, version) 唯一：同一条件的版本号不可重复，与迁移保持一致。
    __table_args__ = (
        UniqueConstraint(
            "conditions_id", "version", name="uq_research_conditions_versions"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conditions_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("research_conditions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    conditions_json: Mapped[str] = mapped_column(Text, nullable=False)
    uncertain_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
