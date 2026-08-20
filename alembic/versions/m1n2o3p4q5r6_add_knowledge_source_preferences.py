"""add knowledge source preferences

Revision ID: m1n2o3p4q5r6
Revises: l4m5n6o7p8q9
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m1n2o3p4q5r6"
down_revision: str | None = "l4m5n6o7p8q9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add independent persisted scheduling and pin preferences for SQLite."""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.add_column(sa.Column("auto_sync", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_knowledge_sources_is_pinned", ["is_pinned"])
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128)))
        batch_op.add_column(sa.Column("lease_owner", sa.String(length=128)))
        batch_op.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
        batch_op.create_index("ix_task_records_idempotency_key", ["idempotency_key"])


def downgrade() -> None:
    """Remove preferences without touching historical migrations."""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_index("ix_knowledge_sources_is_pinned")
        batch_op.drop_column("is_pinned")
        batch_op.drop_column("auto_sync")
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.drop_index("ix_task_records_idempotency_key")
        batch_op.drop_column("heartbeat_at")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_owner")
        batch_op.drop_column("idempotency_key")
