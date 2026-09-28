"""add commercial journal metric contract

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "z3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "literature_commercial_journal_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_key", sa.String(length=500), nullable=False),
        sa.Column("provider", sa.String(length=100)),
        sa.Column("provider_version", sa.String(length=100)),
        sa.Column("license_provenance", sa.Text()),
        sa.Column("metric_year", sa.Integer()),
        sa.Column("impact_factor", sa.Float()),
        sa.Column("indexing_status", sa.String(length=30)),
        sa.Column("quartile", sa.String(length=10)),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "journal_key",
            "provider",
            "metric_year",
            "provider_version",
            name="uq_literature_commercial_journal_metric_snapshot",
        ),
    )
    op.create_index(
        "ix_literature_commercial_journal_metric_lookup",
        "literature_commercial_journal_metrics",
        ["journal_key", "metric_year"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_literature_commercial_journal_metric_lookup",
        table_name="literature_commercial_journal_metrics",
    )
    op.drop_table("literature_commercial_journal_metrics")
