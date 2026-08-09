"""add model privacy settings

Revision ID: d2f60a9c7b14
Revises: c7a31d8b4e05
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "d2f60a9c7b14"
down_revision: str | None = "c7a31d8b4e05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    with op.batch_alter_table("model_configs") as batch:
        batch.add_column(
            sa.Column(
                "deployment_mode", sa.String(16), nullable=False, server_default="local"
            )
        )
        batch.add_column(
            sa.Column(
                "provider", sa.String(32), nullable=False, server_default="ollama"
            )
        )
        batch.add_column(
            sa.Column(
                "api_base",
                sa.Text(),
                nullable=False,
                server_default="http://localhost:11434",
            )
        )
        batch.add_column(sa.Column("encrypted_api_key", sa.Text()))
        batch.add_column(
            sa.Column(
                "model_name",
                sa.String(200),
                nullable=False,
                server_default="unconfigured",
            )
        )
        batch.add_column(
            sa.Column(
                "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch.add_column(
            sa.Column(
                "allow_cloud_content",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
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
    op.create_index(
        "uq_model_configs_default",
        "model_configs",
        ["is_default"],
        unique=True,
        sqlite_where=sa.text("is_default = 1"),
    )


def downgrade():
    op.drop_index("uq_model_configs_default", table_name="model_configs")
    with op.batch_alter_table("model_configs") as batch:
        for name in (
            "updated_at",
            "created_at",
            "allow_cloud_content",
            "is_default",
            "model_name",
            "encrypted_api_key",
            "api_base",
            "provider",
            "deployment_mode",
        ):
            batch.drop_column(name)
