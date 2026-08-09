"""Add versioned writing projects and isolated user materials."""

import sqlalchemy as sa

from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "writing_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("writing_type", sa.String(length=32), nullable=False),
        sa.Column("generated_content_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
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
    op.create_table(
        "writing_user_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_document_id", sa.Integer()),
    )
    op.create_index(
        "ix_writing_user_materials_project_id", "writing_user_materials", ["project_id"]
    )
    op.create_table(
        "writing_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_version", sa.Integer()),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_writing_versions_project_version"
        ),
    )
    op.create_index(
        "ix_writing_versions_project_id", "writing_versions", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_writing_versions_project_id", table_name="writing_versions")
    op.drop_table("writing_versions")
    op.drop_index(
        "ix_writing_user_materials_project_id", table_name="writing_user_materials"
    )
    op.drop_table("writing_user_materials")
    op.drop_table("writing_projects")
