"""allow persisted recommendations without a confirmed intent

Revision ID: g0b1c2d3e4f5
Revises: f9a0b1c2d3e4
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g0b1c2d3e4f5"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    with op.batch_alter_table("recommendation_runs") as batch_op:
        batch_op.alter_column("intent_snapshot_id", existing_type=sa.Integer(), nullable=True)
def downgrade() -> None:
    op.execute("DELETE FROM recommendation_runs WHERE intent_snapshot_id IS NULL")
    with op.batch_alter_table("recommendation_runs") as batch_op:
        batch_op.alter_column("intent_snapshot_id", existing_type=sa.Integer(), nullable=False)
