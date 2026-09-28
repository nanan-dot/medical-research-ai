"""merge translation and document identity migration heads

Revision ID: e9c5b7d3f2a1
Revises: d8e4f6a1b2c3, d6f4a8c2e9b1
Create Date: 2026-09-01
"""

from collections.abc import Sequence

revision: str = "e9c5b7d3f2a1"
down_revision: tuple[str, str] = ("d8e4f6a1b2c3", "d6f4a8c2e9b1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
