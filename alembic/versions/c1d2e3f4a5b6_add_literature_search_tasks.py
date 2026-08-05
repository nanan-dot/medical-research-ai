"""add literature search tasks and result versions

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    """创建检索任务表与任务-结果版本关联表。

    设计说明：任务表保存检索过程的输入快照（原始主题/结构化条件/检索式/筛选/
    模型版本/用户修改），结果通过 task_results 关联表引用 literature_search_results，
    避免把 items_json 复制进任务表造成历史膨胀。latest_result_id 为冗余外键，
    便于列表页直接展示最近一次成功执行的结果。
    """
    op.create_table(
        "literature_search_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("structured_query", sa.Text(), nullable=False, server_default=""),
        sa.Column("search_string", sa.Text(), nullable=False),
        sa.Column("database", sa.Text(), nullable=False, server_default="pubmed"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retmax", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("filters", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("user_edits", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("searched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "latest_result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id"),
            nullable=True,
        ),
    )
    op.create_table(
        "literature_search_task_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade():
    """回滚时先删关联表，再删任务表（外键顺序）。"""
    op.drop_table("literature_search_task_results")
    op.drop_table("literature_search_tasks")
