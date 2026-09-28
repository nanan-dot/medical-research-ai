"""add versioned recommendation reason snapshots

Revision ID: j1k2l3m4n5o6
Revises: f9a0b1c2d3e4
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: str | Sequence[str] | None = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, column in (
        ("base_reason_json", sa.Column("base_reason_json", sa.Text())),
        ("reason_fact_packet_json", sa.Column("reason_fact_packet_json", sa.Text())),
        ("polished_reason_json", sa.Column("polished_reason_json", sa.Text())),
        ("display_reason_source", sa.Column("display_reason_source", sa.Text(), nullable=False, server_default="base")),
        ("narration_status", sa.Column("narration_status", sa.Text(), nullable=False, server_default="not_requested")),
        ("narration_model", sa.Column("narration_model", sa.Text())),
        ("narration_error_code", sa.Column("narration_error_code", sa.Text())),
        ("narration_fingerprint", sa.Column("narration_fingerprint", sa.Text())),
        ("polished_at", sa.Column("polished_at", sa.DateTime(timezone=True))),
    ):
        op.add_column("recommendation_candidates", column)


def downgrade() -> None:
    for name in ("polished_at", "narration_fingerprint", "narration_error_code", "narration_model", "narration_status", "display_reason_source", "polished_reason_json", "reason_fact_packet_json", "base_reason_json"):
        op.drop_column("recommendation_candidates", name)
