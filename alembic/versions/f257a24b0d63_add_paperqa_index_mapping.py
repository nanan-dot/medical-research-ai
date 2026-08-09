"""add paperqa index mapping

Revision ID: f257a24b0d63
Revises: e146f13a9c52
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f257a24b0d63"
down_revision: str | None = "e146f13a9c52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("paperqa_index_key", sa.String(length=128)))
        batch_op.add_column(sa.Column("paperqa_version", sa.String(length=64)))
        batch_op.add_column(sa.Column("indexed_hash", sa.String(length=64)))
        batch_op.add_column(sa.Column("index_error", sa.Text()))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("index_error")
        batch_op.drop_column("indexed_hash")
        batch_op.drop_column("paperqa_version")
        batch_op.drop_column("paperqa_index_key")
