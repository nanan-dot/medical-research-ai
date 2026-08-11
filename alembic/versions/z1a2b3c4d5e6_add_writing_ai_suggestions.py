"""Add auditable unconfirmed AI writing suggestions."""

import sqlalchemy as sa

from alembic import op

revision = "z1a2b3c4d5e6"
down_revision = "f8a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("writing_ai_suggestions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("writing_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("task", sa.String(length=16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("evidence_mappings_json", sa.Text(), nullable=False), sa.Column("requires_human_confirmation", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("confirmed_at", sa.DateTime(timezone=True)), sa.Column("adopted_version", sa.Integer()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_writing_ai_suggestions_project_id", "writing_ai_suggestions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_writing_ai_suggestions_project_id", table_name="writing_ai_suggestions")
    op.drop_table("writing_ai_suggestions")
