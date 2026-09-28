"""Add immutable A1 layout segmentation derived tables.

Revision ID: a19f8e7d6c5b
Revises: e14d8a06c923
"""

import sqlalchemy as sa

from alembic import op

revision = "a19f8e7d6c5b"
down_revision = "e14d8a06c923"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_segmentation_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "anchor_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("segmentation_fingerprint", sa.String(64)),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column(
            "quality_summary_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.String(500)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "anchor_revision_id", "request_fingerprint", name="uq_segmentation_request"
        ),
    )
    op.create_index(
        "ix_document_segmentation_revisions_anchor_revision_id",
        "document_segmentation_revisions",
        ["anchor_revision_id"],
    )
    op.create_index(
        "ix_document_segmentation_revisions_state",
        "document_segmentation_revisions",
        ["state"],
    )
    op.create_index(
        "uq_segmentation_current_anchor",
        "document_segmentation_revisions",
        ["anchor_revision_id"],
        unique=True,
        sqlite_where=sa.text("state IN ('ready', 'review_required')"),
        postgresql_where=sa.text("state IN ('ready', 'review_required')"),
    )
    op.create_table(
        "document_layout_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segmentation_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "page_id",
            sa.Integer(),
            sa.ForeignKey("document_source_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_order", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("item_indexes_json", sa.Text(), nullable=False),
        sa.Column("bbox_json", sa.Text(), nullable=False),
        sa.Column("quality_flags_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "document_layout_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segmentation_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("literal_title", sa.Text(), nullable=False),
        sa.Column("canonical_role", sa.String(32)),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("first_page", sa.Integer(), nullable=False),
        sa.Column("last_page", sa.Integer(), nullable=False),
    )
    op.create_table(
        "document_layout_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segmentation_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_key", sa.String(64), nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("segment_type", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("section_path_json", sa.Text(), nullable=False),
        sa.Column("translation_eligibility", sa.String(32), nullable=False),
        sa.Column("quality_flags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("first_page", sa.Integer(), nullable=False),
        sa.Column("last_page", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "segmentation_revision_id", "reading_order", name="uq_layout_segment_order"
        ),
    )
    op.create_table(
        "document_layout_fragments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segment_id",
            sa.Integer(),
            sa.ForeignKey("document_layout_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fragment_order", sa.Integer(), nullable=False),
        sa.Column(
            "page_id",
            sa.Integer(),
            sa.ForeignKey("document_source_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_item_index", sa.Integer(), nullable=False),
        sa.Column("end_item_index", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "segment_id", "fragment_order", name="uq_layout_fragment_order"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_layout_fragments")
    op.drop_table("document_layout_segments")
    op.drop_table("document_layout_sections")
    op.drop_table("document_layout_blocks")
    op.drop_index(
        "uq_segmentation_current_anchor", table_name="document_segmentation_revisions"
    )
    op.drop_table("document_segmentation_revisions")
