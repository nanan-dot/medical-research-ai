"""add result-scoped deduplication work views

Revision ID: l4m5n6o7p8q9
Revises: k4d5e6f7a8b
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l4m5n6o7p8q9"
down_revision: str | Sequence[str] | None = "k4d5e6f7a8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """结果级去重工作视图：组绑定结果快照、成员稳定记录身份、阅读顺序按视图隔离。

    全部为增量列/表重建，不删除或改写原始检索结果、用户状态与旧跨任务审计组；
    旧跨任务组（result_id/fingerprint 为 NULL）继续保留可读审计数据。
    """
    # 组绑定不可变结果快照；旧跨任务组这两列为 NULL。
    # SQLite 不支持 ADD COLUMN 内联外键，用 batch 重建方式添加（数据自动拷贝）。
    with op.batch_alter_table("literature_duplicate_groups") as batch_op:
        batch_op.add_column(
            sa.Column(
                "result_id",
                sa.Integer(),
                sa.ForeignKey(
                    "literature_search_results.id",
                    name="fk_literature_duplicate_groups_result_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("fingerprint", sa.Text(), nullable=True)
        )
    op.create_index(
        "ix_literature_duplicate_groups_result_id",
        "literature_duplicate_groups",
        ["result_id"],
    )
    op.create_index(
        "ix_literature_duplicate_groups_fingerprint",
        "literature_duplicate_groups",
        ["fingerprint"],
    )

    # 成员稳定记录身份：结果内位置 + 受控 record_key + 规范记录键。
    op.add_column(
        "literature_duplicate_group_members",
        sa.Column("record_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "literature_duplicate_group_members",
        sa.Column("position", sa.Integer(), nullable=True),
    )
    op.add_column(
        "literature_duplicate_group_members",
        sa.Column("canonical_record_key", sa.Text(), nullable=True),
    )

    # 阅读顺序人工顺序按 duplicate_mode 隔离：旧记录回填 'all'，唯一约束从
    # result_id 换成 (result_id, duplicate_mode)。SQLite 无法就地修改唯一约束，
    # 采用"建新表→拷贝→删旧→改名"的确定性重建，避免依赖无名约束反射。
    op.create_table(
        "literature_reading_orders_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("duplicate_mode", sa.Text(), nullable=False),
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
        sa.UniqueConstraint(
            "result_id",
            "duplicate_mode",
            name="uq_literature_reading_orders_result_duplicate_mode",
        ),
    )
    op.execute(
        "INSERT INTO literature_reading_orders_new "
        "(id, result_id, duplicate_mode, manual_order_json, created_at, updated_at) "
        "SELECT id, result_id, 'all', manual_order_json, created_at, updated_at "
        "FROM literature_reading_orders"
    )
    op.drop_table("literature_reading_orders")
    op.rename_table("literature_reading_orders_new", "literature_reading_orders")

    # 结果扫描时间戳：区分"已扫描（可能无重复）"与"从未扫描"（has_scan=false）。
    op.add_column(
        "literature_search_results",
        sa.Column("dedup_scanned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """只撤销本任务新增结构；原始检索结果与旧跨任务审计组保持不动。"""
    op.drop_column("literature_search_results", "dedup_scanned_at")

    op.create_table(
        "literature_reading_orders_old",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"),
            nullable=False,
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
        sa.UniqueConstraint(
            "result_id", name="uq_literature_reading_orders_result_id"
        ),
    )
    op.execute(
        "INSERT INTO literature_reading_orders_old "
        "(id, result_id, manual_order_json, created_at, updated_at) "
        "SELECT id, result_id, manual_order_json, created_at, updated_at "
        "FROM literature_reading_orders"
    )
    op.drop_table("literature_reading_orders")
    op.rename_table("literature_reading_orders_old", "literature_reading_orders")

    op.drop_column("literature_duplicate_group_members", "canonical_record_key")
    op.drop_column("literature_duplicate_group_members", "position")
    op.drop_column("literature_duplicate_group_members", "record_key")
    op.drop_index(
        "ix_literature_duplicate_groups_fingerprint",
        table_name="literature_duplicate_groups",
    )
    op.drop_index(
        "ix_literature_duplicate_groups_result_id",
        table_name="literature_duplicate_groups",
    )
    # result_id 是外键子列，SQLite 不允许直接 DROP COLUMN，需 batch 重建移除。
    with op.batch_alter_table("literature_duplicate_groups") as batch_op:
        batch_op.drop_column("fingerprint")
        batch_op.drop_column("result_id")
