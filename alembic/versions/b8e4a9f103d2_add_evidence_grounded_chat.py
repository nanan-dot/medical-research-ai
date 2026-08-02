"""add evidence grounded chat

Revision ID: b8e4a9f103d2
Revises: a4c81d7e9201
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b8e4a9f103d2"
down_revision: str | None = "a4c81d7e9201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("document_ids", sa.Text(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("title", sa.String(200)))
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(100)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("feedback", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_message_sequence"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("section", sa.String(300)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("citation_text", sa.Text()),
        sa.Column("retrieval_score", sa.Float()),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])
    op.create_index("ix_citations_document_id", "citations", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_citations_document_id", table_name="citations")
    op.drop_index("ix_citations_message_id", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("title")
        batch.drop_column("document_ids")
