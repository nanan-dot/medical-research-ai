"""add local markdown exports

Revision ID: e9b42c1d6f08
Revises: d2f60a9c7b14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e9b42c1d6f08"
down_revision: str | None = "d2f60a9c7b14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "exports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("export_type", sa.String(32), nullable=False),
        sa.Column("source_ids", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_info", sa.Text()),
        sa.Column("pending_confirmations", sa.Text()),
        sa.Column("local_output_path", sa.Text(), nullable=False),
        sa.UniqueConstraint("local_output_path"),
    )


def downgrade():
    op.drop_table("exports")
