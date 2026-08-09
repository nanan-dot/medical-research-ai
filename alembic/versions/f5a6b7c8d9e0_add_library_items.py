"""add formal local library items

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-05
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Only stores metadata and local-document links; it never retrieves remote full text."""
    op.create_table(
        "library_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pmid", sa.Text(), nullable=False, unique=True),
        sa.Column("doi", sa.Text(), nullable=True, unique=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("journal", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True
        ),
        sa.Column(
            "source_search_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id"),
            nullable=False,
        ),
        sa.Column("fulltext_status", sa.Text(), nullable=False),
        sa.Column("fulltext_status_reason", sa.Text(), nullable=False),
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
    op.create_index("ix_library_items_pmid", "library_items", ["pmid"])
    op.create_index("ix_library_items_doi", "library_items", ["doi"])


def downgrade() -> None:
    op.drop_index("ix_library_items_doi", table_name="library_items")
    op.drop_index("ix_library_items_pmid", table_name="library_items")
    op.drop_table("library_items")
