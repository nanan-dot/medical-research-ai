"""add knowledge source management

Revision ID: b741bb1a6d5c
Revises: 098a8f062646
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b741bb1a6d5c"
down_revision: str | None = "098a8f062646"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=200)))
        batch_op.add_column(sa.Column("source_type", sa.String(length=32)))
        batch_op.add_column(sa.Column("root_path", sa.Text()))
        batch_op.add_column(sa.Column("normalized_root_path", sa.Text()))
        batch_op.add_column(
            sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "sync_status",
                sa.String(length=32),
                server_default="idle",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("last_sync_time", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("error_message", sa.Text()))

    # The R0 skeleton exposed no create endpoint, but preserve any manually inserted id-only rows.
    op.execute(
        sa.text(
            "UPDATE knowledge_sources SET "
            "name = 'Legacy source ' || id, "
            "source_type = 'local_folder', "
            "root_path = '', "
            "normalized_root_path = 'legacy:' || id, "
            "sync_status = 'unavailable', "
            "error_message = 'Legacy record requires a newly authorized directory'"
        )
    )

    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.alter_column(
            "name", existing_type=sa.String(length=200), nullable=False
        )
        batch_op.alter_column(
            "source_type", existing_type=sa.String(length=32), nullable=False
        )
        batch_op.alter_column("root_path", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column(
            "normalized_root_path", existing_type=sa.Text(), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_knowledge_sources_normalized_root_path", ["normalized_root_path"]
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_constraint(
            "uq_knowledge_sources_normalized_root_path", type_="unique"
        )
        batch_op.drop_column("error_message")
        batch_op.drop_column("last_sync_time")
        batch_op.drop_column("sync_status")
        batch_op.drop_column("enabled")
        batch_op.drop_column("normalized_root_path")
        batch_op.drop_column("root_path")
        batch_op.drop_column("source_type")
        batch_op.drop_column("name")
