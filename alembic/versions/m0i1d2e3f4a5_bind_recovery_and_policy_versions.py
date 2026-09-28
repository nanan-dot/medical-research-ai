"""Bind M0 recovery identities and version policy interpretation.

Revision ID: m0i1d2e3f4a5
Revises: m0h1c2d3e4f5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m0i1d2e3f4a5"
down_revision: str | Sequence[str] | None = "m0h1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_artifacts",
        sa.Column(
            "registry_version",
            sa.String(64),
            nullable=False,
            server_default="m0-artifact-registry-v1",
        ),
    )
    op.add_column(
        "user_confirmations",
        sa.Column(
            "policy_version",
            sa.String(64),
            nullable=False,
            server_default="m0-confirmation-policy-v1",
        ),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("research_context_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("input_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("expected_artifact_type", sa.String(96), nullable=True),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("expected_artifact_key", sa.String(128), nullable=True),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("idempotency_record_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "agent_external_executions",
        sa.Column("formal_artifact_id", sa.String(64), nullable=True),
    )
    op.execute(
        "UPDATE agent_external_executions SET research_context_id = "
        "(SELECT research_context_id FROM agent_runs "
        "WHERE agent_runs.run_id = agent_external_executions.run_id), "
        "input_hash = (SELECT input_hash FROM agent_steps "
        "WHERE agent_steps.step_id = agent_external_executions.step_id)"
    )
    with op.batch_alter_table("agent_external_executions") as batch:
        batch.alter_column("research_context_id", nullable=False)
        batch.create_index(
            "ix_external_executions_context", ["research_context_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_external_executions") as batch:
        batch.drop_index("ix_external_executions_context")
    for column in (
        "formal_artifact_id",
        "idempotency_record_id",
        "expected_artifact_key",
        "expected_artifact_type",
        "input_hash",
        "research_context_id",
    ):
        op.drop_column("agent_external_executions", column)
    op.drop_column("user_confirmations", "policy_version")
    op.drop_column("agent_artifacts", "registry_version")
