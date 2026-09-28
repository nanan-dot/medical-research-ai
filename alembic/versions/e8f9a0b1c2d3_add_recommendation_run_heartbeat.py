"""add recommendation run heartbeat

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendation_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_column("recommendation_runs", "heartbeat_at")
