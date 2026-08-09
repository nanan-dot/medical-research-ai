"""add document task states

Revision ID: d935e02f8b41
Revises: c824d91e7a30
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d935e02f8b41"
down_revision: str | None = "c824d91e7a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "parse_status",
                sa.String(length=32),
                server_default="pending",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "index_status",
                sa.String(length=32),
                server_default="pending",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("error_code", sa.String(length=64)))
        batch_op.add_column(sa.Column("error_message", sa.Text()))
        batch_op.add_column(
            sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("finished_at", sa.DateTime(timezone=True)))

    op.execute(
        sa.text(
            "UPDATE documents SET index_status = 'outdated' WHERE scan_state = 'outdated'"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("finished_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("retry_count")
        batch_op.drop_column("error_message")
        batch_op.drop_column("error_code")
        batch_op.drop_column("index_status")
        batch_op.drop_column("parse_status")
