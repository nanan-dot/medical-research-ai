"""Add confidential project flag and AI disclosure records."""

import sqlalchemy as sa
from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("writing_projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "confidential",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("input_scope", sa.String(length=500), nullable=False),
        sa.Column("output_version", sa.String(length=100), nullable=False),
        sa.Column(
            "human_edited", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "is_cloud", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_ai_usage_events_project_id", "ai_usage_events", ["project_id"])
    op.create_table(
        "ai_disclosure_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ai_disclosure_drafts_project_id", "ai_disclosure_drafts", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_disclosure_drafts_project_id", table_name="ai_disclosure_drafts"
    )
    op.drop_table("ai_disclosure_drafts")
    op.drop_index("ix_ai_usage_events_project_id", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
    with op.batch_alter_table("writing_projects") as batch_op:
        batch_op.drop_column("confidential")
