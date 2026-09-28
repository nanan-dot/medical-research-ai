"""add verified PMC open fulltext retrievals

Revision ID: c0e1f2a3b4c5
Revises: b9d0e1f2a3b4
Create Date: 2026-08-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0e1f2a3b4c5"
down_revision: str | None = "b9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("library_items") as batch:
        batch.add_column(sa.Column("pmcid", sa.Text(), nullable=True))
        batch.create_index("ix_library_items_pmcid", ["pmcid"], unique=True)
    op.create_table(
        "fulltext_retrievals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_item_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("pmcid", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("file_format", sa.String(length=24), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["library_item_id"], ["library_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fulltext_retrievals_library_item_id"),
        "fulltext_retrievals",
        ["library_item_id"],
    )
    op.create_index(
        op.f("ix_fulltext_retrievals_pmcid"),
        "fulltext_retrievals",
        ["pmcid"],
    )
    op.create_index(
        op.f("ix_fulltext_retrievals_status"),
        "fulltext_retrievals",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_fulltext_retrievals_status"),
        table_name="fulltext_retrievals",
    )
    op.drop_index(
        op.f("ix_fulltext_retrievals_pmcid"),
        table_name="fulltext_retrievals",
    )
    op.drop_index(
        op.f("ix_fulltext_retrievals_library_item_id"),
        table_name="fulltext_retrievals",
    )
    op.drop_table("fulltext_retrievals")
    with op.batch_alter_table("library_items") as batch:
        batch.drop_index("ix_library_items_pmcid")
        batch.drop_column("pmcid")
