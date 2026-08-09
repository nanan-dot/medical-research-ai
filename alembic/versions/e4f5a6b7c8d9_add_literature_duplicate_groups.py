"""add reversible literature duplicate groups

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存可撤销决策，绝不修改检索结果快照或物理删除原始文献。"""
    op.create_table(
        "literature_duplicate_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trigger_task_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_tasks.id"),
            nullable=False,
        ),
        sa.Column("match_method", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "literature_duplicate_group_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("literature_duplicate_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id"),
            nullable=False,
        ),
        sa.Column("record_pmid", sa.Text(), nullable=False),
        sa.Column("canonical_result_id", sa.Integer(), nullable=True),
        sa.Column("canonical_record_pmid", sa.Text(), nullable=True),
        sa.Column(
            "source_search_ids_json", sa.Text(), nullable=False, server_default="[]"
        ),
    )
    op.create_table(
        "literature_duplicate_resolutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("literature_duplicate_groups.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved_action", sa.Text(), nullable=False),
        sa.Column("resolved_by", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("literature_duplicate_resolutions")
    op.drop_table("literature_duplicate_group_members")
    op.drop_table("literature_duplicate_groups")
