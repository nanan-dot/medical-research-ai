"""add comparison tasks

Revision ID: b6f9a1c3d7e2
Revises: ee5f23856af4
"""
from alembic import op
import sqlalchemy as sa
revision = "b6f9a1c3d7e2"
down_revision = "ee5f23856af4"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("comparison_tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("selected_document_ids", sa.Text(), nullable=False), sa.Column("fields", sa.Text(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("comparison_cells", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("comparison_id", sa.Integer(), sa.ForeignKey("comparison_tasks.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", sa.Integer(), nullable=False), sa.Column("field", sa.String(length=64), nullable=False), sa.Column("cell_value", sa.Text(), nullable=False), sa.Column("sources", sa.Text(), nullable=False), sa.Column("generated_value", sa.Text()), sa.Column("user_value", sa.Text()), sa.Column("status", sa.String(length=32), nullable=False), sa.UniqueConstraint("comparison_id", "document_id", "field", name="uq_comparison_cell"))
    op.create_index("ix_comparison_cells_comparison_id", "comparison_cells", ["comparison_id"])
def downgrade() -> None:
    op.drop_index("ix_comparison_cells_comparison_id", table_name="comparison_cells")
    op.drop_table("comparison_cells")
    op.drop_table("comparison_tasks")
