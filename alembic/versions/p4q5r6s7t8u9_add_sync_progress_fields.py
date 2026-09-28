"""add persistent task sync progress

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "p4q5r6s7t8u9"
down_revision: str | None = "o3p4q5r6s7t8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable/zero-safe progress state to existing task rows."""
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.add_column(
            sa.Column("phase", sa.String(length=32), nullable=False, server_default="queued")
        )
        batch_op.add_column(
            sa.Column("completed_units", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("total_units", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("current_item", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("progress_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove only task progress metadata, preserving task history itself."""
    with op.batch_alter_table("task_records") as batch_op:
        batch_op.drop_column("progress_updated_at")
        batch_op.drop_column("current_item")
        batch_op.drop_column("total_units")
        batch_op.drop_column("completed_units")
        batch_op.drop_column("phase")
