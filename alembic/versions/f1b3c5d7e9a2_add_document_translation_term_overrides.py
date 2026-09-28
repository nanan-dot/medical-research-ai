"""add document-scoped translation term overrides

Revision ID: f1b3c5d7e9a2
Revises: e9c5b7d3f2a1
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1b3c5d7e9a2"
down_revision: str | None = "e9c5b7d3f2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "translation_term_overrides",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("source_term", sa.String(length=256), nullable=False),
        sa.Column("normalized_source_term", sa.String(length=256), nullable=False),
        sa.Column("target_term", sa.String(length=256), nullable=False),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "normalized_source_term",
            "target_language",
            name="uq_translation_term_override_scope",
        ),
    )
    op.create_index(
        op.f("ix_translation_term_overrides_document_id"),
        "translation_term_overrides",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_translation_term_overrides_document_id"),
        table_name="translation_term_overrides",
    )
    op.drop_table("translation_term_overrides")
