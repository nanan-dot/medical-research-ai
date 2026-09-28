"""Persist shared A2 source anchors, coverage, notes and idempotency.

Revision ID: b31a2c4d5e60
Revises: a2f8e7d6c5b4
"""

import sqlalchemy as sa

from alembic import op

revision = "b31a2c4d5e60"
down_revision = "a2f8e7d6c5b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_source_anchors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "anchor_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("anchor_type", sa.String(32), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("normalized_quote", sa.Text(), nullable=False),
        sa.Column("quote_hash", sa.String(64), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("suffix", sa.Text(), nullable=False),
        sa.Column("quality_status", sa.String(32), nullable=False),
        sa.Column("join_version", sa.String(32), nullable=False),
        sa.Column("resolution_status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("content_fingerprint", name="uq_source_anchor_content"),
    )
    op.create_table(
        "document_anchor_fragments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "anchor_id",
            sa.Integer(),
            sa.ForeignKey("document_source_anchors.id", ondelete="CASCADE"),
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
        sa.Column("start_offset_utf16", sa.Integer(), nullable=False),
        sa.Column("end_item_index", sa.Integer(), nullable=False),
        sa.Column("end_offset_utf16", sa.Integer(), nullable=False),
        sa.Column("rectangles_json", sa.Text(), nullable=False),
        sa.Column("reconstructed_text_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "anchor_id", "fragment_order", name="uq_anchor_fragment_order"
        ),
    )
    op.create_table(
        "document_anchor_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "anchor_id",
            sa.Integer(),
            sa.ForeignKey("document_source_anchors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segmentation_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_segmentation_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            sa.Integer(),
            sa.ForeignKey("document_layout_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("coverage_order", sa.Integer(), nullable=False),
        sa.Column("segment_char_start", sa.Integer(), nullable=False),
        sa.Column("segment_char_end", sa.Integer(), nullable=False),
        sa.Column("coverage_type", sa.String(16), nullable=False),
        sa.UniqueConstraint(
            "anchor_id",
            "segmentation_revision_id",
            "coverage_order",
            name="uq_anchor_coverage",
        ),
    )
    op.create_table(
        "document_reading_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_anchor_id",
            sa.Integer(),
            sa.ForeignKey("document_source_anchors.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("quote_snapshot", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "document_selection_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "scope", "operation", "idempotency_key", name="uq_selection_operation"
        ),
    )
    for table, column in [
        ("document_source_anchors", "anchor_revision_id"),
        ("document_anchor_fragments", "anchor_id"),
        ("document_anchor_segments", "anchor_id"),
        ("document_reading_notes", "document_id"),
    ]:
        op.create_index(f"ix_{table}_{column}", table, [column])
    with op.batch_alter_table("document_annotations") as batch:
        batch.add_column(sa.Column("source_anchor_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_annotation_source_anchor",
            "document_source_anchors",
            ["source_anchor_id"],
            ["id"],
        )
        batch.create_index(
            "ix_document_annotations_source_anchor_id", ["source_anchor_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("document_annotations") as batch:
        batch.drop_index("ix_document_annotations_source_anchor_id")
        batch.drop_constraint("fk_annotation_source_anchor", type_="foreignkey")
        batch.drop_column("source_anchor_id")
    for table in [
        "document_selection_operations",
        "document_reading_notes",
        "document_anchor_segments",
        "document_anchor_fragments",
        "document_source_anchors",
    ]:
        op.drop_table(table)
