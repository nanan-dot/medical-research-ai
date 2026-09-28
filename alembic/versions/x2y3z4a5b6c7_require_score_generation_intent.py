"""require score generation intent snapshot

Revision ID: x2y3z4a5b6c7
Revises: w1x2y3z4a5b6
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "x2y3z4a5b6c7"
down_revision: str | None = "w1x2y3z4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.alter_column(
            "intent_snapshot_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.alter_column(
            "intent_snapshot_id", existing_type=sa.Integer(), nullable=True
        )
