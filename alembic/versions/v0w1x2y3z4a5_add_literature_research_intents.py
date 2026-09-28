"""add literature research intent snapshots

Revision ID: v0w1x2y3z4a5
Revises: u9v0w1x2y3z4
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "v0w1x2y3z4a5"
down_revision: str | None = "u9v0w1x2y3z4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "literature_research_intent_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "research_context_id",
            sa.Integer(),
            sa.ForeignKey("research_contexts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("confirmation_status", sa.Text(), nullable=False),
        sa.Column("dimensions_json", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "research_context_id",
            "fingerprint",
            name="uq_literature_intent_context_fingerprint",
        ),
    )
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.create_foreign_key(
            "fk_score_generation_intent",
            "literature_research_intent_snapshots",
            ["intent_snapshot_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.alter_column(
            "intent_snapshot_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_score_generations") as batch_op:
        batch_op.drop_constraint("fk_score_generation_intent", type_="foreignkey")
    op.drop_table("literature_research_intent_snapshots")
