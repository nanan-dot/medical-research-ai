"""Align existing migration indexes with ORM metadata.

Revision ID: n2c3d4e5f6a7
Revises: n1b2c3d4e5f6
"""

from collections.abc import Sequence

from alembic import op

revision: str = "n2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "n1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ORM-declared indexes and correct two pre-existing index definitions."""
    op.create_index(
        "ix_document_file_revisions_is_current",
        "document_file_revisions",
        ["is_current"],
    )
    op.create_index(
        "ix_anchor_relocation_source_target",
        "document_anchor_relocations",
        ["source_anchor_id", "target_anchor_revision_id"],
    )
    op.create_index(
        "ix_document_anchor_relocations_status",
        "document_anchor_relocations",
        ["status"],
    )
    op.drop_index("ix_paper_tag_library_item_id", table_name="paper_tags")
    op.create_index("ix_paper_tags_library_item_id", "paper_tags", ["library_item_id"])
    op.drop_index("ix_paper_work_states_library_item_id", table_name="paper_work_states")
    op.create_index(
        "ix_paper_work_states_library_item_id",
        "paper_work_states",
        ["library_item_id"],
        unique=True,
    )


def downgrade() -> None:
    """Restore the preceding index layout."""
    op.drop_index("ix_paper_work_states_library_item_id", table_name="paper_work_states")
    op.create_index(
        "ix_paper_work_states_library_item_id",
        "paper_work_states",
        ["library_item_id"],
    )
    op.drop_index("ix_paper_tags_library_item_id", table_name="paper_tags")
    op.create_index("ix_paper_tag_library_item_id", "paper_tags", ["library_item_id"])
    op.drop_index(
        "ix_document_anchor_relocations_status",
        table_name="document_anchor_relocations",
    )
    op.drop_index(
        "ix_anchor_relocation_source_target",
        table_name="document_anchor_relocations",
    )
    op.drop_index(
        "ix_document_file_revisions_is_current",
        table_name="document_file_revisions",
    )
