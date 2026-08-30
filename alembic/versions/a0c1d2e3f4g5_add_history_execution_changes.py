"""add persisted history execution result changes

Revision ID: a0c1d2e3f4g5
Revises: i2j3k4l5m6n
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0c1d2e3f4g5"
down_revision: str | None = "i2j3k4l5m6n"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_search_executions") as batch_op:
        batch_op.add_column(sa.Column("previous_result_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("added_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("removed_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("added_pmids_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("removed_pmids_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("has_changes", sa.Boolean(), nullable=True))
        batch_op.create_foreign_key(
            "fk_literature_search_executions_previous_result_id",
            "literature_search_results", ["previous_result_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_search_executions") as batch_op:
        batch_op.drop_constraint("fk_literature_search_executions_previous_result_id", type_="foreignkey")
        batch_op.drop_column("has_changes")
        batch_op.drop_column("removed_pmids_json")
        batch_op.drop_column("added_pmids_json")
        batch_op.drop_column("removed_count")
        batch_op.drop_column("added_count")
        batch_op.drop_column("previous_result_id")
