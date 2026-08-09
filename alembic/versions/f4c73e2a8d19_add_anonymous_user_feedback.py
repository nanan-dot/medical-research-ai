"""add anonymous user feedback

Revision ID: f4c73e2a8d19
Revises: e9b42c1d6f08
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "f4c73e2a8d19"
down_revision: str | None = "e9b42c1d6f08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    with op.batch_alter_table("feedbacks") as batch:
        batch.add_column(
            sa.Column(
                "task_completion_rate", sa.Float(), nullable=False, server_default="0"
            )
        )
        batch.add_column(sa.Column("useful", sa.Boolean()))
        batch.add_column(sa.Column("citation_correct", sa.Boolean()))
        batch.add_column(sa.Column("data_correct", sa.Boolean()))
        batch.add_column(sa.Column("error_type", sa.String(32)))
        batch.add_column(sa.Column("comment", sa.Text()))
        batch.add_column(sa.Column("next_step", sa.Text()))
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )


def downgrade():
    with op.batch_alter_table("feedbacks") as batch:
        for name in (
            "created_at",
            "next_step",
            "comment",
            "error_type",
            "data_correct",
            "citation_correct",
            "useful",
            "task_completion_rate",
        ):
            batch.drop_column(name)
