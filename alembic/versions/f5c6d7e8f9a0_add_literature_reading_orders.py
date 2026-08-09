"""add literature reading order manual persistence

Revision ID: f5c6d7e8f9a0
Revises: f5a6b7c8d9e0
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5c6d7e8f9a0"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存用户拖拽后的人工顺序（完整 PMID 列表 JSON）。

    设计说明：表只持久化"人工顺序"这一用户态；算法顺序每次生成时由规则
    分类器实时计算，不落库。result_id 唯一约束保证同一结果快照只保留一份
    人工顺序，重新生成阅读顺序时读取它并优先应用（不覆盖人工顺序）。
    """
    op.create_table(
        "literature_reading_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("manual_order_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("literature_reading_orders")
