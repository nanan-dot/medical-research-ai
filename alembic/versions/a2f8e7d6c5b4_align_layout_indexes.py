"""Align A1 layout indexes with ORM metadata.

Revision ID: a2f8e7d6c5b4
Revises: a19f8e7d6c5b
"""

from alembic import op

revision = "a2f8e7d6c5b4"
down_revision = "a19f8e7d6c5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("document_layout_blocks", "page_id"),
        ("document_layout_blocks", "segmentation_revision_id"),
        ("document_layout_fragments", "page_id"),
        ("document_layout_fragments", "segment_id"),
        ("document_layout_sections", "segmentation_revision_id"),
        ("document_layout_segments", "segment_key"),
        ("document_layout_segments", "segmentation_revision_id"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])
    with op.batch_alter_table("document_segmentation_revisions") as batch:
        batch.alter_column("created_at", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("document_segmentation_revisions") as batch:
        batch.alter_column("created_at", nullable=True)
    for table, column in (
        ("document_layout_segments", "segmentation_revision_id"),
        ("document_layout_segments", "segment_key"),
        ("document_layout_sections", "segmentation_revision_id"),
        ("document_layout_fragments", "segment_id"),
        ("document_layout_fragments", "page_id"),
        ("document_layout_blocks", "segmentation_revision_id"),
        ("document_layout_blocks", "page_id"),
    ):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
