"""add persisted search strategy workspace

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "s7t8u9v0w1x2"
down_revision: str | None = "r6s7t8u9v0w1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create drafts independently from immutable task result snapshots."""
    op.create_table(
        "search_strategy_drafts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_question", sa.Text(), nullable=False),
        sa.Column("intent_mode", sa.Text(), nullable=False),
        sa.Column("intent_json", sa.Text(), nullable=False),
        sa.Column("limits_json", sa.Text(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_source", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("generation_state", sa.Text(), nullable=False),
        sa.Column("validation_state", sa.Text(), nullable=False),
        sa.Column("count_state", sa.Text(), nullable=False),
        sa.Column("count_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_search_strategy_drafts_fingerprint", "search_strategy_drafts", ["fingerprint"])
    op.create_table(
        "search_strategy_terms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_group", sa.Text(), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False), sa.Column("field_tag", sa.Text()), sa.Column("relation_type", sa.Text()),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("warning_code", sa.Text()), sa.Column("warning_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_search_strategy_terms_strategy_id", "search_strategy_terms", ["strategy_id"])
    op.create_table(
        "search_strategy_mesh_terms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("descriptor", sa.Text(), nullable=False), sa.Column("mesh_id", sa.Text()), sa.Column("concept_group", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False), sa.Column("verification_status", sa.Text(), nullable=False), sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_checked_at", sa.DateTime(timezone=True)), sa.Column("metadata_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_search_strategy_mesh_terms_strategy_id", "search_strategy_mesh_terms", ["strategy_id"])
    op.create_table(
        "search_strategy_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("search_strategy_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("snapshot_json", sa.Text(), nullable=False), sa.Column("fingerprint", sa.Text(), nullable=False), sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("strategy_id", "version", name="uq_search_strategy_version"),
    )
    op.create_index("ix_search_strategy_versions_strategy_id", "search_strategy_versions", ["strategy_id"])


def downgrade() -> None:
    """Remove only newly introduced strategy-domain tables."""
    op.drop_index("ix_search_strategy_versions_strategy_id", table_name="search_strategy_versions")
    op.drop_table("search_strategy_versions")
    op.drop_index("ix_search_strategy_mesh_terms_strategy_id", table_name="search_strategy_mesh_terms")
    op.drop_table("search_strategy_mesh_terms")
    op.drop_index("ix_search_strategy_terms_strategy_id", table_name="search_strategy_terms")
    op.drop_table("search_strategy_terms")
    op.drop_index("ix_search_strategy_drafts_fingerprint", table_name="search_strategy_drafts")
    op.drop_table("search_strategy_drafts")
