"""add unique active task idempotency key

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "r6s7t8u9v0w1"
down_revision: str | None = "q5r6s7t8u9v0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为活动任务建立数据库级幂等约束，历史终态任务保持可重复。"""
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.add_column(sa.Column("active_idempotency_key", sa.String(length=128)))
        batch_op.create_unique_constraint(
            "uq_task_records_active_idempotency_key", ["active_idempotency_key"]
        )


def downgrade() -> None:
    """仅移除活动键约束，不删除任务记录。"""
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.drop_constraint("uq_task_records_active_idempotency_key", type_="unique")
        batch_op.drop_column("active_idempotency_key")
