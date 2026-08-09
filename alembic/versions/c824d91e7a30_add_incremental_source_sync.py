"""add incremental source synchronization

Revision ID: c824d91e7a30
Revises: b741bb1a6d5c
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c824d91e7a30"
down_revision: str | None = "b741bb1a6d5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.add_column(
            sa.Column("sync_added", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("sync_modified", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("sync_deleted", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("sync_skipped", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("sync_failed", sa.Integer(), server_default="0", nullable=False)
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column("knowledge_source_id", sa.Integer(), nullable=False)
        )
        batch_op.add_column(sa.Column("file_path", sa.Text(), nullable=False))
        batch_op.add_column(
            sa.Column("normalized_file_path", sa.Text(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("file_hash", sa.String(length=64), nullable=False)
        )
        batch_op.add_column(sa.Column("file_size", sa.BigInteger(), nullable=False))
        batch_op.add_column(
            sa.Column("modified_time", sa.DateTime(timezone=True), nullable=False)
        )
        batch_op.add_column(
            sa.Column("modified_time_ns", sa.BigInteger(), nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "scan_state",
                sa.String(length=32),
                server_default="pending",
                nullable=False,
            )
        )
        batch_op.create_foreign_key(
            "fk_documents_knowledge_source_id",
            "knowledge_sources",
            ["knowledge_source_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_documents_knowledge_source_id", ["knowledge_source_id"]
        )
        batch_op.create_unique_constraint(
            "uq_documents_source_path", ["knowledge_source_id", "normalized_file_path"]
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("uq_documents_source_path", type_="unique")
        batch_op.drop_index("ix_documents_knowledge_source_id")
        batch_op.drop_constraint("fk_documents_knowledge_source_id", type_="foreignkey")
        batch_op.drop_column("scan_state")
        batch_op.drop_column("modified_time_ns")
        batch_op.drop_column("modified_time")
        batch_op.drop_column("file_size")
        batch_op.drop_column("file_hash")
        batch_op.drop_column("normalized_file_path")
        batch_op.drop_column("file_path")
        batch_op.drop_column("knowledge_source_id")

    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_column("sync_failed")
        batch_op.drop_column("sync_skipped")
        batch_op.drop_column("sync_deleted")
        batch_op.drop_column("sync_modified")
        batch_op.drop_column("sync_added")
