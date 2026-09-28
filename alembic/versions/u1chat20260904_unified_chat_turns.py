"""统一科研对话轮次和本地知识缺口。"""

import sqlalchemy as sa

from alembic import op

revision = "u1chat20260904"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "unified_chat_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("active_key", sa.Integer(), unique=True),
        sa.Column("deadline", sa.Float(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column(
            "user_message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assistant_message_id",
            sa.Integer(),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
        ),
        sa.Column("response_json", sa.Text()),
        sa.UniqueConstraint(
            "conversation_id", "request_id", name="uq_unified_turn_request"
        ),
    )
    op.create_index(
        "ix_unified_chat_turns_conversation_id",
        "unified_chat_turns",
        ["conversation_id"],
    )
    op.create_table(
        "unified_knowledge_gaps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("document_ids", sa.Text(), nullable=False),
        sa.Column(
            "research_context_id",
            sa.Integer(),
            sa.ForeignKey("research_contexts.id", ondelete="CASCADE"),
        ),
        sa.Column("occurrences", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("unified_knowledge_gaps")
    op.drop_index(
        "ix_unified_chat_turns_conversation_id", table_name="unified_chat_turns"
    )
    op.drop_table("unified_chat_turns")
