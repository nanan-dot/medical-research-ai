"""add document annotations

Revision ID: a8c9d0e1f2a3
Revises: f7b8c9d0e1f2
Create Date: 2026-08-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8c9d0e1f2a3"
down_revision: str | None = "f7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("selection_geometry", sa.Text(), nullable=False),
        sa.Column("selected_text", sa.Text(), nullable=False),
        sa.Column("selected_text_hash", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_annotations_document_id"), "document_annotations", ["document_id"])
    op.create_index(op.f("ix_document_annotations_file_hash"), "document_annotations", ["file_hash"])


def downgrade() -> None:
    op.drop_index(op.f("ix_document_annotations_file_hash"), table_name="document_annotations")
    op.drop_index(op.f("ix_document_annotations_document_id"), table_name="document_annotations")
    op.drop_table("document_annotations")
