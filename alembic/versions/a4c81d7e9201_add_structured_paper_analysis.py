"""add structured paper analysis

Revision ID: a4c81d7e9201
Revises: f257a24b0d63
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4c81d7e9201"
down_revision: str | None = "f257a24b0d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("paper_analysiss") as batch_op:
        batch_op.add_column(sa.Column("document_id", sa.Integer(), nullable=False))
        batch_op.add_column(
            sa.Column(
                "analysis_status",
                sa.String(32),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "template_version",
                sa.String(32),
                nullable=False,
                server_default="general-v1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "model_version", sa.String(64), nullable=False, server_default="unknown"
            )
        )
        batch_op.add_column(
            sa.Column("generation", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("structured_result", sa.Text()))
        batch_op.add_column(sa.Column("sources", sa.Text()))
        batch_op.add_column(sa.Column("pending_confirmations", sa.Text()))
        batch_op.add_column(sa.Column("error_code", sa.String(64)))
        batch_op.add_column(sa.Column("error_message", sa.Text()))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_index("ix_paper_analysiss_document_id", ["document_id"])
        batch_op.create_foreign_key(
            "fk_paper_analysiss_document_id",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("paper_analysiss") as batch_op:
        batch_op.drop_constraint("fk_paper_analysiss_document_id", type_="foreignkey")
        batch_op.drop_index("ix_paper_analysiss_document_id")
        for name in (
            "updated_at",
            "created_at",
            "error_message",
            "error_code",
            "pending_confirmations",
            "sources",
            "structured_result",
            "generation",
            "model_version",
            "template_version",
            "analysis_status",
            "document_id",
        ):
            batch_op.drop_column(name)
