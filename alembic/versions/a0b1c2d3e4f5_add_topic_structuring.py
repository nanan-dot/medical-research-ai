"""add topic structuring snapshots

Revision ID: a0b1c2d3e4f5
Revises: ee5f23856af4, a9e1c2d3f4b5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: tuple[str, str] = ("ee5f23856af4", "a9e1c2d3f4b5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_structurings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("original_topic", sa.Text(), nullable=False),
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
        "topic_structuring_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_structuring_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("structured_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_structuring_id"], ["topic_structurings.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "topic_structuring_id", "version", name="uq_topic_structuring_versions"
        ),
    )


def downgrade() -> None:
    op.drop_table("topic_structuring_versions")
    op.drop_table("topic_structurings")
