"""add evidence-grounded research directions

Revision ID: a3d4e5f6a7b8
Revises: a0b1c2d3f4b5
"""

import sqlalchemy as sa
from alembic import op

revision = "a3d4e5f6a7b8"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("research_directions")
    }
    expected_columns = {
        "research_conditions_id", "evidence_matrix_id", "name", "question", "research_object",
        "study_type", "evidence_json", "current_evidence", "current_evidence_sources_json",
        "controversy", "controversy_sources_json", "gap", "novelty_uncertainty", "priority",
        "generation_strategy", "methods", "requirements", "difficulty", "time_risk",
        "resource_risk", "ethics_risk", "search_terms", "advisor_questions",
        "generation_metadata_json", "merged_from_ids_json", "status", "merged_into_id",
        "version", "created_at", "updated_at",
    }
    # 兼容曾绕过 Alembic 创建完整表的开发库；空库中的占位表仍走下方建表路径。
    if expected_columns.issubset(existing_columns):
        return
    if existing_columns != {"id"}:
        raise RuntimeError("research_directions has a partial schema; resolve it before upgrading")
    # 初始迁移已建了仅含 id 的占位表；batch 模式会在 SQLite 中安全重建该表。
    existing_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM research_directions")
    ).scalar_one()
    if existing_count:
        raise RuntimeError(
            "research_directions contains legacy rows; migrate them explicitly before R3-WP04"
        )
    with op.batch_alter_table("research_directions") as batch_op:
        batch_op.add_column(sa.Column("research_conditions_id", sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column("evidence_matrix_id", sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column("name", sa.String(length=300), nullable=False))
        batch_op.add_column(sa.Column("question", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("research_object", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("study_type", sa.String(length=100), nullable=False))
        batch_op.add_column(sa.Column("evidence_json", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("current_evidence", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("current_evidence_sources_json", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("controversy", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("controversy_sources_json", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("gap", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("novelty_uncertainty", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("priority", sa.String(length=32), nullable=False))
        batch_op.add_column(sa.Column("generation_strategy", sa.String(length=32), nullable=False))
        batch_op.add_column(sa.Column("methods", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("requirements", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("difficulty", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("time_risk", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("resource_risk", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("ethics_risk", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("search_terms", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("advisor_questions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("generation_metadata_json", sa.Text(), nullable=False))
        batch_op.add_column(sa.Column("merged_from_ids_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
        batch_op.add_column(sa.Column("merged_into_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        batch_op.create_foreign_key("fk_research_directions_conditions", "research_conditions", ["research_conditions_id"], ["id"])
        batch_op.create_foreign_key("fk_research_directions_matrix", "evidence_matrices", ["evidence_matrix_id"], ["id"])
        batch_op.create_foreign_key("fk_research_directions_merged_into", "research_directions", ["merged_into_id"], ["id"])
        batch_op.create_index("ix_research_directions_conditions_id", ["research_conditions_id"])
        batch_op.create_index("ix_research_directions_matrix_id", ["evidence_matrix_id"])


def downgrade() -> None:
    with op.batch_alter_table("research_directions") as batch_op:
        batch_op.drop_index("ix_research_directions_matrix_id")
        batch_op.drop_index("ix_research_directions_conditions_id")
        batch_op.drop_constraint("fk_research_directions_merged_into", type_="foreignkey")
        batch_op.drop_constraint("fk_research_directions_matrix", type_="foreignkey")
        batch_op.drop_constraint("fk_research_directions_conditions", type_="foreignkey")
        for column_name in (
            "updated_at", "created_at", "version", "merged_into_id", "status", "merged_from_ids_json",
            "generation_metadata_json", "advisor_questions", "search_terms", "ethics_risk", "resource_risk",
            "time_risk", "difficulty", "requirements", "methods", "generation_strategy", "priority",
            "novelty_uncertainty", "gap", "controversy_sources_json", "controversy",
            "current_evidence_sources_json", "current_evidence", "evidence_json", "study_type",
            "research_object", "question", "name", "evidence_matrix_id", "research_conditions_id",
        ):
            batch_op.drop_column(column_name)
