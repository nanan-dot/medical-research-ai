"""add paper library v3.1 runtime fields

Revision ID: a2c4e6f8b0d1
Revises: f1b3c5d7e9a2
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2c4e6f8b0d1"
down_revision: str | None = "f1b3c5d7e9a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("paper_analysiss") as batch:
        batch.add_column(sa.Column("task_set_version", sa.String(64)))
        batch.add_column(sa.Column("task_names_json", sa.Text()))
        batch.add_column(sa.Column("completed_task_names_json", sa.Text()))

    with op.batch_alter_table("library_items") as batch:
        batch.add_column(sa.Column("journal_quartile_source", sa.Text()))
        batch.add_column(sa.Column("journal_quartile_year", sa.Integer()))
        batch.add_column(
            sa.Column(
                "metadata_status",
                sa.Text(),
                nullable=False,
                server_default="pending",
            )
        )
        batch.add_column(sa.Column("metadata_source", sa.Text()))
        batch.add_column(sa.Column("metadata_error_code", sa.Text()))
        batch.add_column(sa.Column("metadata_error_message", sa.Text()))
        batch.add_column(
            sa.Column(
                "metadata_retry_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(sa.Column("metadata_last_attempt_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("library_items") as batch:
        batch.drop_column("metadata_last_attempt_at")
        batch.drop_column("metadata_retry_count")
        batch.drop_column("metadata_error_message")
        batch.drop_column("metadata_error_code")
        batch.drop_column("metadata_source")
        batch.drop_column("metadata_status")
        batch.drop_column("journal_quartile_year")
        batch.drop_column("journal_quartile_source")

    with op.batch_alter_table("paper_analysiss") as batch:
        batch.drop_column("completed_task_names_json")
        batch.drop_column("task_names_json")
        batch.drop_column("task_set_version")
