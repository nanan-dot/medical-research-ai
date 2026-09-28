"""论文库专属的持久化状态与关系模型。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaperLibraryMember(Base):
    """记录被用户明确纳入论文库的条目，隔离检索收藏与论文工作区。"""

    __tablename__ = "paper_library_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    import_source: Mapped[str] = mapped_column(String(32), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PaperWorkState(Base):
    """正式论文的工作状态独立于检索结果，避免检索历史删除时丢失进度。"""

    __tablename__ = "paper_work_states"
    __table_args__ = (
        CheckConstraint(
            "reading_progress_percent >= 0 AND reading_progress_percent <= 100",
            name="ck_paper_work_state_progress",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    reading_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unread"
    )
    reading_progress_percent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    current_section: Mapped[str | None] = mapped_column(String(200))
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_analysis_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_work_kind: Mapped[str | None] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PaperResearchRelation(Base):
    """角色归属在论文与研究的关系上，因此同一论文可服务多个研究。"""

    __tablename__ = "paper_research_relations"
    __table_args__ = (
        UniqueConstraint(
            "library_item_id", "research_context_id", name="uq_paper_research_relation"
        ),
        Index("ix_paper_research_relation_context_role", "research_context_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    research_context_id: Mapped[int] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
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


class PaperActivity(Base):
    """只记录服务层写入的真实论文工作事件，列表和概览从此表投影。"""

    __tablename__ = "paper_activities"
    __table_args__ = (
        Index("ix_paper_activity_item_created", "library_item_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_scope: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="local:default",
        server_default="local:default",
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PaperResearchCenterPreference(Base):
    """Actor-scoped explicit current research selection and its workflow stage."""

    __tablename__ = "paper_research_center_preferences"
    __table_args__ = (
        UniqueConstraint("actor_scope", name="uq_paper_center_preference_actor"),
        CheckConstraint(
            "stage IN ('problem_definition','literature_reading','paper_understanding',"
            "'evidence_organization','conclusion_formation')",
            name="ck_paper_center_preference_stage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_scope: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    research_context_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="SET NULL"), index=True
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PaperTag(Base):
    """使用规范化关联表保存标签，确保筛选语义和数据库方言无关。"""

    __tablename__ = "paper_tags"
    __table_args__ = (
        UniqueConstraint("library_item_id", "name", name="uq_paper_tag_item_name"),
        Index("ix_paper_tag_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
