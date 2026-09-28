"""add durable knowledge source auto-sync scheduling state

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q5r6s7t8u9v0"
down_revision: str | None = "p4q5r6s7t8u9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增可空调度时间，存量来源默认仍为关闭自动同步。"""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.add_column(
            sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="60")
        )
        batch_op.add_column(sa.Column("next_auto_sync_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("last_auto_sync_enqueued_at", sa.DateTime(timezone=True)))
        batch_op.add_column(
            sa.Column("auto_sync_failure_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index(
            "ix_knowledge_sources_auto_sync_due",
            ["auto_sync", "enabled", "next_auto_sync_at"],
        )


def downgrade() -> None:
    """仅移除调度元数据，不触碰知识源和任务主数据。"""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_index("ix_knowledge_sources_auto_sync_due")
        batch_op.drop_column("auto_sync_failure_count")
        batch_op.drop_column("last_auto_sync_enqueued_at")
        batch_op.drop_column("next_auto_sync_at")
        batch_op.drop_column("sync_interval_minutes")
