"""Add A0 source maps/quality and enforce one current revision.

Revision ID: e14d8a06c923
Revises: a0a1b2c3d4e5
"""

import sqlalchemy as sa

from alembic import op

revision = "e14d8a06c923"
down_revision = "a0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, default in (
        ("styles_json", "{}"),
        ("quality_metrics_json", "{}"),
        ("char_map_json", "[]"),
    ):
        op.add_column(
            "document_source_pages",
            sa.Column(name, sa.Text(), nullable=False, server_default=default),
        )
    for name in ("char_map_json", "bbox_json"):
        op.add_column(
            "document_source_text_items",
            sa.Column(name, sa.Text(), nullable=False, server_default="[]"),
        )
    op.add_column(
        "document_source_text_items",
        sa.Column("raw_utf16_length", sa.Integer(), nullable=False, server_default="0"),
    )
    # 旧规范缺少映射，保留记录用于追溯，但不能作为新规范下的当前结果。
    op.execute(
        "UPDATE document_anchor_revisions SET state='stale' WHERE state IN ('ready','review_required')"
    )
    op.create_index(
        "uq_anchor_current_document",
        "document_anchor_revisions",
        ["document_id"],
        unique=True,
        sqlite_where=sa.text("state IN ('ready','review_required')"),
        postgresql_where=sa.text("state IN ('ready','review_required')"),
    )


def downgrade() -> None:
    op.drop_index("uq_anchor_current_document", table_name="document_anchor_revisions")
    with op.batch_alter_table("document_source_text_items") as batch:
        for name in ("raw_utf16_length", "bbox_json", "char_map_json"):
            batch.drop_column(name)
    with op.batch_alter_table("document_source_pages") as batch:
        for name in ("char_map_json", "quality_metrics_json", "styles_json"):
            batch.drop_column(name)
