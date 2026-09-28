"""add versioned core reading plans and read timestamps

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: str | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_search_item_state") as batch_op:
        batch_op.add_column(sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE literature_search_item_state SET read_status = 'unread' WHERE read_status = 'reading'")
    op.create_table(
        "reading_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("generation_basis_json", sa.Text(), nullable=False),
        sa.Column("duplicate_mode", sa.Text(), nullable=False),
        sa.Column("target_core_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("result_id", "version", name="uq_reading_plan_result_version"),
    )
    op.create_index("ix_reading_plan_active", "reading_plans", ["result_id", "status"])
    op.create_table(
        "reading_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("reading_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pmid", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("recommendation_reason", sa.Text(), nullable=False),
        sa.Column("evidence_features_json", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("plan_id", "pmid", name="uq_reading_plan_item_plan_pmid"),
    )
    op.create_index("ix_reading_plan_item_stage_role", "reading_plan_items", ["plan_id", "stage", "role", "stage_order"])


def downgrade() -> None:
    op.drop_index("ix_reading_plan_item_stage_role", table_name="reading_plan_items")
    op.drop_table("reading_plan_items")
    op.drop_index("ix_reading_plan_active", table_name="reading_plans")
    op.drop_table("reading_plans")
    with op.batch_alter_table("literature_search_item_state") as batch_op:
        batch_op.drop_column("read_at")
