"""add normalized paper tags

Revision ID: c5a7e2d9f1b3
Revises: b4e8d1c7a6f2
"""

import sqlalchemy as sa

from alembic import op

revision = "c5a7e2d9f1b3"
down_revision = "b4e8d1c7a6f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("library_item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["library_item_id"], ["library_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_item_id", "name", name="uq_paper_tag_item_name"),
    )
    op.create_index("ix_paper_tag_library_item_id", "paper_tags", ["library_item_id"])
    op.create_index("ix_paper_tag_name", "paper_tags", ["name"])


def downgrade() -> None:
    op.drop_index("ix_paper_tag_name", table_name="paper_tags")
    op.drop_index("ix_paper_tag_library_item_id", table_name="paper_tags")
    op.drop_table("paper_tags")
