"""add literature search item state

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    """创建检索结果用户态表（R2-WP05，manage-refs 融合）。

    设计说明：items_json 是检索时刻的只读快照，用户"已保存/已读/标签/
    自定义排序序号"写入本表而不回写快照，避免污染可复现的检索记录。
    主键用 result_id + pmid 复合键（同一结果快照内 PMID 唯一）；result
    删除时级联清理用户态，避免孤儿数据。tags 存 JSON 字符串。
    """
    op.create_table(
        "literature_search_item_state",
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey(
                "literature_search_results.id", ondelete="CASCADE"
            ),
            primary_key=True,
        ),
        sa.Column("pmid", sa.Text(), primary_key=True),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "read_status",
            sa.Text(),
            nullable=False,
            server_default="unread",
        ),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("custom_order_index", sa.Integer(), nullable=True),
    )


def downgrade():
    """回滚：删除用户态表（外键级联在删表时一并处理）。"""
    op.drop_table("literature_search_item_state")
