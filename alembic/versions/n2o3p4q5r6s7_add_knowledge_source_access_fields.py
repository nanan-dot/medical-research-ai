"""add knowledge source access fields

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n2o3p4q5r6s7"
down_revision: str | None = "m1n2o3p4q5r6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist actual source access data for the recent-source navigation."""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.add_column(sa.Column("last_opened_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("last_opened_by", sa.String(length=128)))
        batch_op.create_index("ix_knowledge_sources_last_opened_at", ["last_opened_at"])


def downgrade() -> None:
    """Remove access fields when rolling the migration back."""
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_index("ix_knowledge_sources_last_opened_at")
        batch_op.drop_column("last_opened_by")
        batch_op.drop_column("last_opened_at")
