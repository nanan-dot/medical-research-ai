"""add evaluation run persistence

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("evaluation_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("dataset_version", sa.String(100), nullable=False), sa.Column("config_json", sa.Text(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("evaluation_run_results", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_id", sa.Integer(), nullable=False), sa.Column("question_id", sa.String(100), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("raw_output", sa.Text()), sa.Column("elapsed_ms", sa.Integer(), nullable=False), sa.Column("error", sa.Text()))
    op.create_index("ix_evaluation_run_results_run_id", "evaluation_run_results", ["run_id"])
def downgrade() -> None:
    op.drop_index("ix_evaluation_run_results_run_id", table_name="evaluation_run_results")
    op.drop_table("evaluation_run_results")
    op.drop_table("evaluation_runs")
