"""merge library history and recommendation reason migration heads.

Revision ID: k2l3m4n5o6p
Revises: a0c1d2e3f4g5, j1k2l3m4n5o6
"""

from collections.abc import Sequence

revision: str = "k2l3m4n5o6p"
down_revision: str | Sequence[str] | None = ("a0c1d2e3f4g5", "j1k2l3m4n5o6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge-only revision: both parent schemas are retained unchanged."""


def downgrade() -> None:
    """Alembic restores the two parent heads when this merge is downgraded."""
