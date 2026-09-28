"""add persisted OpenAlex score metrics

Revision ID: y3z4a5b6c7d8
Revises: x2y3z4a5b6c7
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "y3z4a5b6c7d8"
down_revision: str | None = "x2y3z4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("literature_article_scores") as batch_op:
        batch_op.add_column(
            sa.Column(
                "citation_metrics_json", sa.Text(), nullable=False, server_default="{}"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("literature_article_scores") as batch_op:
        batch_op.drop_column("citation_metrics_json")
