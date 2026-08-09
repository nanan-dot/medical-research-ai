"""add unified task records

Revision ID: d4e5f6a7b8c9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建通用任务记录表及常用筛选索引。"""
    op.create_table(
        "task_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_records_status", "task_records", ["status"])
    op.create_index("ix_task_records_task_type", "task_records", ["task_type"])


def downgrade() -> None:
    """移除通用任务记录表及其索引。"""
    op.drop_index("ix_task_records_task_type", table_name="task_records")
    op.drop_index("ix_task_records_status", table_name="task_records")
    op.drop_table("task_records")
