"""Persistence entities for editable evidence matrices.

R2-WP12 规范化存储：不用 JSON 大字段存矩阵数据，拆为四张独立表，避免
后期对 JSON 字段做迁移。删除字段时用 inactive 标记而非物理删除，历史
单元格数据保留（matrix_cells 始终按 field_key 挂载，即使字段已停用）。
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvidenceMatrix(Base):
    """一张可编辑的证据矩阵（综述/开题/方向分析的结构化文献表）。

    version 自 1 起递增；regenerate 只更新 generated 单元格并递增版本，
    人工编辑与删除的字段快照不会被新版本覆盖。
    """

    __tablename__ = "evidence_matrices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 状态机：draft / active / archived；archive 不删除数据。
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # 当前矩阵版本，regenerate 时递增。
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 来源任务（可选）：由 comparison task 创建矩阵时的关联，保留可追溯性。
    source_comparison_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("comparison_tasks.id"), nullable=True
    )
    research_context_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("research_contexts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


class MatrixDocument(Base):
    """矩阵中的一篇文献及该文献的用户态字段。

    设计说明（manage-refs 融合）：user_notes / topic_relevance 属于用户
    工作状态，与单元格的模型生成值隔离存放；reading_status（未读/在读/
    已读）与 document_status（已收录/待核验）是两个独立字段，互不耦合。
    document_id 复用 WP11 语义——指向 library_items.id（"已保存文档"），
    保证可基于 comparison task 创建矩阵（两者共享同一批 library items）。
    """

    __tablename__ = "matrix_documents"
    __table_args__ = (
        UniqueConstraint("matrix_id", "document_id", name="uq_matrix_documents"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matrix_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # 用户备注：独立存储，绝不写入单元格的生成值字段。
    user_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 课题相关度：低/中/高；仅记录用户选择的等级，不推断。
    topic_relevance: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )
    # 阅读状态：unread / reading / read。
    reading_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unread"
    )
    # 文献状态：included（已收录）/ pending（待核验）。
    document_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="included"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class MatrixField(Base):
    """矩阵的一个比较字段。

    active=False 表示字段已停用（用户删除）。单元格数据不随字段删除而
    清除：matrix_cells 仍保留该 field_key 的历史值，停用字段不再出现在
    导出与重新生成中。
    """

    __tablename__ = "matrix_fields"
    __table_args__ = (
        UniqueConstraint("matrix_id", "field_key", name="uq_matrix_fields"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matrix_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    field_label: Mapped[str] = mapped_column(String(200), nullable=False)
    # 展示顺序（新增字段追加在末尾）。
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # 停用标记：删除字段 = 置 False，不物理删除。
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class MatrixCell(Base):
    """矩阵中"字段 x 文献"交点的单元格值。

    复用 WP11 区分模式：cell_value 为展示值，user_value 优先；generated_value
    为模型生成值；sources 绑定真实 PMID/DOI。status 三态：generated /
    user_edited / missing。无来源的生成值必须置 missing，绝不编造医学数据。
    """

    __tablename__ = "matrix_cells"
    __table_args__ = (
        UniqueConstraint(
            "matrix_id", "document_id", "field_key", name="uq_matrix_cells"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matrix_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    cell_value: Mapped[str] = mapped_column(Text, nullable=False)
    # 来源 JSON 数组（见 schema.SourceRef）；模型生成的来源可追溯。
    sources: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    generated_value: Mapped[str | None] = mapped_column(Text)
    user_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
