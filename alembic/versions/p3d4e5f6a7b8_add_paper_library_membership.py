"""Separate explicit paper-library membership from saved search records.

Revision ID: p3d4e5f6a7b8
Revises: n2c3d4e5f6a7
"""

import sqlalchemy as sa

from alembic import op

revision = "p3d4e5f6a7b8"
down_revision = "n2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create an empty membership table so historical saved results stay excluded."""
    op.create_table(
        "paper_library_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "library_item_id",
            sa.Integer(),
            sa.ForeignKey("library_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("import_source", sa.String(32), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_paper_library_members_library_item_id",
        "paper_library_members",
        ["library_item_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_library_members_library_item_id",
        table_name="paper_library_members",
    )
    op.drop_table("paper_library_members")
