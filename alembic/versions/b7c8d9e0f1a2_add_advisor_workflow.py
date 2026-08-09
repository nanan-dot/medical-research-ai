"""Add advisor review records and immutable direction revision snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advisor_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "direction_id",
            sa.Integer(),
            sa.ForeignKey("research_directions.id"),
            nullable=False,
        ),
        sa.Column("reviewer_type", sa.String(16), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("points_json", sa.Text(), nullable=False),
        sa.Column("literature_gaps_json", sa.Text(), nullable=False),
        sa.Column("experiment_conditions_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_advisor_reviews_direction_id", "advisor_reviews", ["direction_id"]
    )
    op.create_table(
        "direction_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "direction_id",
            sa.Integer(),
            sa.ForeignKey("research_directions.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "revision_parent_id", sa.Integer(), sa.ForeignKey("direction_revisions.id")
        ),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "direction_id", "version", name="uq_direction_revision_version"
        ),
    )
    op.create_index(
        "ix_direction_revisions_direction_id", "direction_revisions", ["direction_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_direction_revisions_direction_id", table_name="direction_revisions"
    )
    op.drop_table("direction_revisions")
    op.drop_index("ix_advisor_reviews_direction_id", table_name="advisor_reviews")
    op.drop_table("advisor_reviews")
