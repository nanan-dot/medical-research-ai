"""add explicit paper research center preference

Revision ID: t4u5v6w7x8y9
Revises: s2f3g4h5i6j7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "t4u5v6w7x8y9"
down_revision: str | None = "s2f3g4h5i6j7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("paper_activities") as batch_op:
        batch_op.add_column(
            sa.Column(
                "actor_scope",
                sa.String(length=128),
                nullable=False,
                server_default="local:default",
            )
        )
        batch_op.create_index("ix_paper_activities_actor_scope", ["actor_scope"])
    op.create_table(
        "paper_research_center_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_scope", sa.String(length=128), nullable=False),
        sa.Column(
            "research_context_id",
            sa.Integer(),
            sa.ForeignKey("research_contexts.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "stage",
            sa.String(length=32),
            nullable=False,
            server_default="problem_definition",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("actor_scope", name="uq_paper_center_preference_actor"),
        sa.CheckConstraint(
            "stage IN ('problem_definition','literature_reading','paper_understanding','evidence_organization','conclusion_formation')",
            name="ck_paper_center_preference_stage",
        ),
    )
    op.create_index(
        "ix_paper_research_center_preferences_actor_scope",
        "paper_research_center_preferences",
        ["actor_scope"],
    )
    op.create_index(
        "ix_paper_research_center_preferences_research_context_id",
        "paper_research_center_preferences",
        ["research_context_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table("paper_activities") as batch_op:
        batch_op.drop_index("ix_paper_activities_actor_scope")
        batch_op.drop_column("actor_scope")
    op.drop_index(
        "ix_paper_research_center_preferences_research_context_id",
        table_name="paper_research_center_preferences",
    )
    op.drop_index(
        "ix_paper_research_center_preferences_actor_scope",
        table_name="paper_research_center_preferences",
    )
    op.drop_table("paper_research_center_preferences")
