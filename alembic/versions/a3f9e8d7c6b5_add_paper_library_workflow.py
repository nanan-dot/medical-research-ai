"""Add durable paper-library workflow state and research relations.

Revision ID: a3f9e8d7c6b5
Revises: c42d3e4f5a61
"""

import sqlalchemy as sa

from alembic import op

revision = "a3f9e8d7c6b5"
down_revision = "c42d3e4f5a61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("library_items") as batch:
        batch.alter_column("source_search_id", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("authors", sa.Text(), nullable=True))
        batch.add_column(sa.Column("paper_type", sa.Text(), nullable=True))
        batch.add_column(sa.Column("journal_quartile", sa.Text(), nullable=True))
    op.create_table(
        "paper_work_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("reading_status", sa.String(16), nullable=False, server_default="unread"),
        sa.Column("reading_progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_section", sa.String(200)),
        sa.Column("last_read_at", sa.DateTime(timezone=True)), sa.Column("last_analysis_at", sa.DateTime(timezone=True)),
        sa.Column("last_work_kind", sa.String(16)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("reading_progress_percent >= 0 AND reading_progress_percent <= 100", name="ck_paper_work_state_progress"),
    )
    op.create_index("ix_paper_work_states_library_item_id", "paper_work_states", ["library_item_id"])
    op.create_table(
        "paper_research_relations",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_context_id", sa.Integer(), sa.ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32)), sa.Column("note", sa.Text()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("library_item_id", "research_context_id", name="uq_paper_research_relation"),
    )
    op.create_index("ix_paper_research_relations_library_item_id", "paper_research_relations", ["library_item_id"])
    op.create_index("ix_paper_research_relations_research_context_id", "paper_research_relations", ["research_context_id"])
    op.create_index("ix_paper_research_relation_context_role", "paper_research_relations", ["research_context_id", "role"])
    op.create_table(
        "paper_activities",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False), sa.Column("detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_paper_activities_library_item_id", "paper_activities", ["library_item_id"])
    op.create_index("ix_paper_activity_item_created", "paper_activities", ["library_item_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_paper_activity_item_created", table_name="paper_activities")
    op.drop_index("ix_paper_activities_library_item_id", table_name="paper_activities")
    op.drop_table("paper_activities")
    op.drop_index("ix_paper_research_relation_context_role", table_name="paper_research_relations")
    op.drop_index("ix_paper_research_relations_research_context_id", table_name="paper_research_relations")
    op.drop_index("ix_paper_research_relations_library_item_id", table_name="paper_research_relations")
    op.drop_table("paper_research_relations")
    op.drop_index("ix_paper_work_states_library_item_id", table_name="paper_work_states")
    op.drop_table("paper_work_states")
    with op.batch_alter_table("library_items") as batch:
        batch.drop_column("journal_quartile")
        batch.drop_column("paper_type")
        batch.drop_column("authors")
        batch.alter_column("source_search_id", existing_type=sa.Integer(), nullable=False)
