"""add knowledge source research-context links

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o3p4q5r6s7t8"
down_revision: str | None = "n2o3p4q5r6s7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create only the association table; source and context data remain intact."""
    op.create_table(
        "knowledge_source_research_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_source_id", sa.Integer(), nullable=False),
        sa.Column("research_context_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_id"], ["knowledge_sources.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["research_context_id"], ["research_contexts.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "knowledge_source_id",
            "research_context_id",
            name="uq_knowledge_source_research_context",
        ),
    )
    op.create_index(
        "ix_ksrc_knowledge_source_id",
        "knowledge_source_research_contexts",
        ["knowledge_source_id"],
    )
    op.create_index(
        "ix_ksrc_research_context_id",
        "knowledge_source_research_contexts",
        ["research_context_id"],
    )


def downgrade() -> None:
    """Remove only derived association records, not sources or research contexts."""
    op.drop_index("ix_ksrc_research_context_id", table_name="knowledge_source_research_contexts")
    op.drop_index("ix_ksrc_knowledge_source_id", table_name="knowledge_source_research_contexts")
    op.drop_table("knowledge_source_research_contexts")
