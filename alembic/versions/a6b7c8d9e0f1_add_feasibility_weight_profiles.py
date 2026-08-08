"""Add the auditable default feasibility weight profile.

Revision ID: a6b7c8d9e0f1
Revises: a5b6c7d8e9f0
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "a6b7c8d9e0f1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None

DEFAULT_WEIGHTS = {
    "literature_base": 1.0,
    "novelty_uncertainty": 1.0,
    "technical_feasibility": 1.0,
    "sample_availability": 1.0,
    "data_availability": 1.0,
    "timeline": 1.0,
    "budget": 1.0,
    "ethics": 1.0,
    "analysis_difficulty": 1.0,
    "advisor_alignment": 1.0,
}


def upgrade() -> None:
    op.create_table(
        "feasibility_weight_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("weights_json", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.bulk_insert(
        sa.table(
            "feasibility_weight_profiles",
            sa.column("name", sa.String),
            sa.column("weights_json", sa.Text),
            sa.column("rationale", sa.Text),
            sa.column("is_default", sa.Boolean),
        ),
        [
            {
                "name": "Default equal weights",
                "weights_json": json.dumps(DEFAULT_WEIGHTS),
                "rationale": "Initial equal weighting across all ten dimensions.",
                "is_default": True,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("feasibility_weight_profiles")
