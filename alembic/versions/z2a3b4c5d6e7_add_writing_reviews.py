"""Add structured simulated writing reviews."""

import sqlalchemy as sa

from alembic import op

revision = "z2a3b4c5d6e7"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "writing_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "simulated", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("reviewer_label", sa.String(length=100), nullable=False),
        sa.Column("findings_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_writing_reviews_project_id", "writing_reviews", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_writing_reviews_project_id", table_name="writing_reviews")
    op.drop_table("writing_reviews")
