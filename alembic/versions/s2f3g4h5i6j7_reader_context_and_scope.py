"""persist reader Copilot context and scope favorite state by actor

Revision ID: s2f3g4h5i6j7
Revises: r1e2a3d4e5r6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "s2f3g4h5i6j7"
down_revision: str | None = "r1e2a3d4e5r6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table(
        "paper_reader_states",
        recreate="always",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch:
        batch.drop_constraint("uq_paper_reader_states_library_item_id", type_="unique")
        batch.create_unique_constraint(
            "uq_reader_state_scope_item", ["actor_scope", "library_item_id"]
        )
    with op.batch_alter_table("messages", recreate="always") as batch:
        batch.add_column(sa.Column("reader_document_id", sa.Integer()))
        batch.add_column(sa.Column("reader_source_anchor_id", sa.Integer()))
        batch.add_column(sa.Column("reader_active_segment_id", sa.Integer()))
        batch.add_column(sa.Column("reader_section_id", sa.Integer()))
        batch.add_column(sa.Column("reader_anchor_revision_id", sa.Integer()))
        batch.add_column(sa.Column("reader_segmentation_revision_id", sa.Integer()))
        batch.create_foreign_key("fk_messages_reader_document", "documents", ["reader_document_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_messages_reader_source_anchor", "document_source_anchors", ["reader_source_anchor_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_messages_reader_active_segment", "document_layout_segments", ["reader_active_segment_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_messages_reader_section", "document_layout_sections", ["reader_section_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_messages_reader_anchor_revision", "document_anchor_revisions", ["reader_anchor_revision_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_messages_reader_segmentation_revision", "document_segmentation_revisions", ["reader_segmentation_revision_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_messages_reader_document_id", "messages", ["reader_document_id"])
    op.create_index("ix_messages_reader_source_anchor_id", "messages", ["reader_source_anchor_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_reader_source_anchor_id", table_name="messages")
    op.drop_index("ix_messages_reader_document_id", table_name="messages")
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("fk_messages_reader_segmentation_revision", type_="foreignkey")
        batch.drop_constraint("fk_messages_reader_anchor_revision", type_="foreignkey")
        batch.drop_constraint("fk_messages_reader_section", type_="foreignkey")
        batch.drop_constraint("fk_messages_reader_active_segment", type_="foreignkey")
        batch.drop_constraint("fk_messages_reader_source_anchor", type_="foreignkey")
        batch.drop_constraint("fk_messages_reader_document", type_="foreignkey")
        batch.drop_column("reader_segmentation_revision_id")
        batch.drop_column("reader_anchor_revision_id")
        batch.drop_column("reader_section_id")
        batch.drop_column("reader_active_segment_id")
        batch.drop_column("reader_source_anchor_id")
        batch.drop_column("reader_document_id")
    with op.batch_alter_table("paper_reader_states", recreate="always") as batch:
        batch.drop_constraint("uq_reader_state_scope_item", type_="unique")
        batch.create_unique_constraint("uq_paper_reader_states_library_item_id", ["library_item_id"])
