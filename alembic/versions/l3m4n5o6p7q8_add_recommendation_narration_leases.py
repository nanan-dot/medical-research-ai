"""add recommendation narration leases

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l3m4n5o6p7q8"
down_revision: str | Sequence[str] | None = "k2l3m4n5o6p"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_narration_leases",
        sa.Column("fingerprint", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("claim_token", sa.Text()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("polished_reason_json", sa.Text()),
        sa.Column("narration_model", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_narration_leases")
