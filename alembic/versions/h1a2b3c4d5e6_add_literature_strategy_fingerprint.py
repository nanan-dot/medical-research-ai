"""Add exact strategy fingerprints without rewriting history.

Revision ID: h1a2b3c4d5e6
Revises: z2a3b4c5d6e7
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h1a2b3c4d5e6"
down_revision: str | None = "z2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable unique fingerprint; null retains all audit rows."""
    op.add_column("literature_search_tasks", sa.Column("strategy_fingerprint", sa.Text(), nullable=True))
    op.create_index("ix_literature_search_tasks_strategy_fingerprint", "literature_search_tasks", ["strategy_fingerprint"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_literature_search_tasks_strategy_fingerprint", table_name="literature_search_tasks")
    op.drop_column("literature_search_tasks", "strategy_fingerprint")
