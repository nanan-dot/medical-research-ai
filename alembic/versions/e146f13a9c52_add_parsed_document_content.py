"""add parsed document content

Revision ID: e146f13a9c52
Revises: d935e02f8b41
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e146f13a9c52"
down_revision: str | None = "d935e02f8b41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("parsed_title", sa.String(length=500)))
        batch_op.add_column(sa.Column("parsed_content", sa.Text()))
        batch_op.add_column(sa.Column("parsed_is_scanned", sa.Boolean()))
        batch_op.add_column(sa.Column("parsed_page_count", sa.Integer()))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("parsed_page_count")
        batch_op.drop_column("parsed_is_scanned")
        batch_op.drop_column("parsed_content")
        batch_op.drop_column("parsed_title")
