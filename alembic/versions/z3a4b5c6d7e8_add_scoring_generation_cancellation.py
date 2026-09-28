"""add scoring generation cancellation state

Revision ID: z3a4b5c6d7e8
Revises: y3z4a5b6c7d8
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "z3a4b5c6d7e8"
down_revision: str | None = "y3z4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cancel_requested",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "request_options_json", sa.Text(), nullable=False, server_default="{}"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.drop_column("request_options_json")
        batch_op.drop_column("cancel_requested")
