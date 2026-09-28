"""Allow verified DOI or document papers without a PMID.

Revision ID: b4e8d1c7a6f2
Revises: a3f9e8d7c6b5
"""

import sqlalchemy as sa

from alembic import op

revision = "b4e8d1c7a6f2"
down_revision = "a3f9e8d7c6b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("library_items") as batch:
        batch.alter_column("pmid", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    identifier_only_count = connection.execute(sa.text("SELECT COUNT(*) FROM library_items WHERE pmid IS NULL")).scalar_one()
    if identifier_only_count:
        raise RuntimeError("DOWNGRADE_WOULD_LOSE_IDENTIFIER_ONLY_PAPERS")
    with op.batch_alter_table("library_items") as batch:
        batch.alter_column("pmid", existing_type=sa.Text(), nullable=False)
