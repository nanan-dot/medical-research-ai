"""add no answer state

Revision ID: c7a31d8b4e05
Revises: b8e4a9f103d2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7a31d8b4e05"
down_revision: str | None = "b8e4a9f103d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("answer_status", sa.String(32)))
        batch.add_column(sa.Column("uncertainty", sa.Float()))
        batch.add_column(sa.Column("reason_codes", sa.Text()))


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("reason_codes")
        batch.drop_column("uncertainty")
        batch.drop_column("answer_status")
