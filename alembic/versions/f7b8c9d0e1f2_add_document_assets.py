"""add document assets

Revision ID: f7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("asset_kind", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_relative_path", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_relative_path"),
    )
    # 模型层 document_id 声明为 index=True, unique=True（生成唯一索引），
    # 此处对齐为唯一索引；不能用 UniqueConstraint（会产生约束而非索引，导致漂移）。
    op.create_index(
        op.f("ix_document_assets_document_id"),
        "document_assets",
        ["document_id"],
        unique=True,
    )
    op.create_index(op.f("ix_document_assets_sha256"), "document_assets", ["sha256"])


def downgrade() -> None:
    op.drop_index(op.f("ix_document_assets_sha256"), table_name="document_assets")
    op.drop_index(op.f("ix_document_assets_document_id"), table_name="document_assets")
    op.drop_table("document_assets")
