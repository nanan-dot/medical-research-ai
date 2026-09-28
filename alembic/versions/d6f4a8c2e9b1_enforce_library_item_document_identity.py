"""Enforce one formal paper per linked document.

Revision ID: d6f4a8c2e9b1
Revises: c5a7e2d9f1b3
"""

import sqlalchemy as sa

from alembic import op

revision = "d6f4a8c2e9b1"
down_revision = "c5a7e2d9f1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicate_document_ids = connection.execute(
        sa.text(
            "SELECT document_id FROM library_items WHERE document_id IS NOT NULL "
            "GROUP BY document_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).scalar_one_or_none()
    if duplicate_document_ids is not None:
        raise RuntimeError("LIBRARY_ITEM_DOCUMENT_IDENTITY_CONFLICT")
    with op.batch_alter_table("library_items") as batch:
        batch.create_unique_constraint(
            "uq_library_items_document_id", ["document_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("library_items") as batch:
        batch.drop_constraint("uq_library_items_document_id", type_="unique")
