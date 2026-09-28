"""add A0 PDF.js text item anchor revisions

Revision ID: a0a1b2c3d4e5
Revises: m4n5o6p7q8r9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a0a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "m4n5o6p7q8r9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_anchor_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("extraction_fingerprint", sa.String(length=64)),
        sa.Column("extractor_version", sa.String(length=64), nullable=False),
        sa.Column("pdfjs_version", sa.String(length=64), nullable=False),
        sa.Column("normalization_version", sa.String(length=64), nullable=False),
        sa.Column("options_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "quality_summary_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("error_message", sa.String(length=500)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "document_id", "request_fingerprint", name="uq_anchor_revision_request"
        ),
        sa.UniqueConstraint(
            "document_id",
            "file_hash",
            "extraction_fingerprint",
            name="uq_anchor_revision_complete",
        ),
    )
    op.create_index(
        "ix_document_anchor_revisions_document_id",
        "document_anchor_revisions",
        ["document_id"],
    )
    op.create_index(
        "ix_document_anchor_revisions_state", "document_anchor_revisions", ["state"]
    )
    op.create_table(
        "document_source_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Integer(), nullable=False),
        sa.Column("view_box_json", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("text_item_count", sa.Integer(), nullable=False),
        sa.Column("quality_flags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.UniqueConstraint(
            "revision_id", "page_number", name="uq_source_page_revision_number"
        ),
    )
    op.create_index(
        "ix_document_source_pages_revision_id", "document_source_pages", ["revision_id"]
    )
    op.create_table(
        "document_source_text_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "page_id",
            sa.Integer(),
            sa.ForeignKey("document_source_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("source_array_index", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("transform_json", sa.Text(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("has_eol", sa.Boolean(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("font_name", sa.String(length=256)),
        sa.Column("normalized_char_start", sa.Integer(), nullable=False),
        sa.Column("normalized_char_end", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "page_id", "item_index", name="uq_source_text_item_page_index"
        ),
    )
    op.create_index(
        "ix_document_source_text_items_page_id",
        "document_source_text_items",
        ["page_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_source_text_items_page_id", table_name="document_source_text_items"
    )
    op.drop_table("document_source_text_items")
    op.drop_index(
        "ix_document_source_pages_revision_id", table_name="document_source_pages"
    )
    op.drop_table("document_source_pages")
    op.drop_index(
        "ix_document_anchor_revisions_state", table_name="document_anchor_revisions"
    )
    op.drop_index(
        "ix_document_anchor_revisions_document_id",
        table_name="document_anchor_revisions",
    )
    op.drop_table("document_anchor_revisions")
