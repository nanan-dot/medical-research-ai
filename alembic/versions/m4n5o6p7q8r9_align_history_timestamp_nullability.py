"""align history timestamp nullability

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m4n5o6p7q8r9"
down_revision: str | Sequence[str] | None = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


_TIMESTAMP_COLUMNS = {
    "literature_search_executions": ("created_at",),
    "literature_search_strategies": ("created_at", "updated_at"),
    "literature_search_strategy_versions": ("created_at",),
}


def _alter_nullable(nullable: bool) -> None:
    for table_name, columns in _TIMESTAMP_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch:
            for column_name in columns:
                batch.alter_column(
                    column_name,
                    existing_type=sa.DateTime(timezone=True),
                    existing_server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=nullable,
                )


def upgrade() -> None:
    _alter_nullable(nullable=False)


def downgrade() -> None:
    _alter_nullable(nullable=True)
