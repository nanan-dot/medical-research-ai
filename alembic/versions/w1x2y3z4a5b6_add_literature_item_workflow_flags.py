"""add literature item workflow flags

Revision ID: w1x2y3z4a5b6
Revises: v0w1x2y3z4a5
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "w1x2y3z4a5b6"
down_revision: str | None = "v0w1x2y3z4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_search_item_state") as batch_op:
        batch_op.add_column(
            sa.Column(
                "in_reading_plan",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("is_key", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_search_item_state") as batch_op:
        batch_op.drop_column("is_key")
        batch_op.drop_column("in_reading_plan")
