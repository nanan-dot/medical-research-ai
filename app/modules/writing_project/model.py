"""写作项目、生成内容、用户材料与不可变版本快照模型。"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WritingProject(Base):
    __tablename__ = "writing_projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    writing_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    research_context_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
    materials: Mapped[list["WritingUserMaterial"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    generated_content: Mapped["WritingGeneratedContent"] = relationship(
        cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    snapshots: Mapped[list["WritingVersion"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    evidence_references: Mapped[list["WritingEvidenceReference"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class WritingUserMaterial(Base):
    __tablename__ = "writing_user_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # 仅保存外部资产标识，不建立级联外键；删除项目绝不能删除知识库来源。
    source_document_id: Mapped[int | None] = mapped_column(Integer)


class WritingGeneratedContent(Base):
    __tablename__ = "writing_generated_contents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    content_json: Mapped[str] = mapped_column(Text, nullable=False)


class WritingVersion(Base):
    __tablename__ = "writing_versions"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "version", name="uq_writing_versions_project_version"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class WritingEvidenceReference(Base):
    """A paragraph-level reference whose location is copied from a real source."""

    __tablename__ = "writing_evidence_references"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("writing_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_citation_id: Mapped[int | None] = mapped_column(
        ForeignKey("citations.id", ondelete="SET NULL"), nullable=True
    )
    matrix_cell_id: Mapped[int | None] = mapped_column(
        ForeignKey("matrix_cells.id", ondelete="SET NULL"), nullable=True
    )
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(300))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    citation_text: Mapped[str | None] = mapped_column(Text)
    pmid: Mapped[str | None] = mapped_column(String(64))
    doi: Mapped[str | None] = mapped_column(String(300))
    locator: Mapped[str | None] = mapped_column(String(300))
