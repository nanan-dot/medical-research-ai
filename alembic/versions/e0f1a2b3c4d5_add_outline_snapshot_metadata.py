"""Add evidence-matrix snapshot metadata to outlines."""

import sqlalchemy as sa

from alembic import op

revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("outlines") as batch_op:
        batch_op.add_column(
            sa.Column(
                "based_on_matrix_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "retrieval_date",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "document_count", sa.Integer(), nullable=False, server_default="0"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("outlines") as batch_op:
        batch_op.drop_column("document_count")
        batch_op.drop_column("retrieval_date")
        batch_op.drop_column("based_on_matrix_version")
