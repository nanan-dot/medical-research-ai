"""add research conditions snapshots

Revision ID: a9e1c2d3f4b5
Revises: c7d8e9f0a1b2
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9e1c2d3f4b5"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_conditions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "research_conditions_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conditions_id",
            sa.Integer(),
            sa.ForeignKey("research_conditions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("uncertain_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "conditions_id", "version", name="uq_research_conditions_versions"
        ),
    )


def downgrade() -> None:
    op.drop_table("research_conditions_versions")
    op.drop_table("research_conditions")
