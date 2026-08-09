"""Separate generated writing content from project metadata.

The downgrade restores the legacy column but drops the normalized table; callers
must treat downgrade as a destructive schema operation and back up the database.
"""

import sqlalchemy as sa
from alembic import op

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "writing_generated_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("writing_projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("content_json", sa.Text(), nullable=False),
    )
    op.execute(
        sa.text(
            "INSERT INTO writing_generated_contents (project_id, content_json) "
            "SELECT id, generated_content_json FROM writing_projects"
        )
    )
    with op.batch_alter_table("writing_projects") as batch_op:
        batch_op.drop_column("generated_content_json")


def downgrade() -> None:
    with op.batch_alter_table("writing_projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "generated_content_json", sa.Text(), nullable=False, server_default="{}"
            )
        )
    op.execute(
        sa.text(
            "UPDATE writing_projects SET generated_content_json = "
            "(SELECT content_json FROM writing_generated_contents "
            "WHERE writing_generated_contents.project_id = writing_projects.id)"
        )
    )
    op.drop_table("writing_generated_contents")
