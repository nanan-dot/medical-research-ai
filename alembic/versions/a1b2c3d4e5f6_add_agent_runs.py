"""persist agent runs, approval state, and minimal audit traces.

Revision ID: aa1b2c3d4e5f
Revises: z3a4b5c6d7e8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "aa1b2c3d4e5f"
down_revision: str | None = "z3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REQUIRED_COLUMNS = {
    "run_id",
    "workflow_status",
    "state_json",
    "events_json",
    "retrieval_trace_json",
    "created_at",
    "updated_at",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_runs" in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns("agent_runs")}
        missing = _REQUIRED_COLUMNS - existing
        if missing:
            raise RuntimeError(
                "existing agent_runs does not match the legacy contract: "
                + ", ".join(sorted(missing))
            )
        return

    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_status", sa.String(length=32), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("events_json", sa.JSON(), nullable=False),
        sa.Column("retrieval_trace_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_workflow_status", "agent_runs", ["workflow_status"])
    op.create_table(
        "agent_runs_migration_ownership",
        sa.Column("revision", sa.String(32), primary_key=True),
    )
    op.execute(
        sa.text(
            "INSERT INTO agent_runs_migration_ownership (revision) "
            "VALUES ('aa1b2c3d4e5f')"
        )
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "agent_runs_migration_ownership" not in inspector.get_table_names():
        return
    op.drop_table("agent_runs_migration_ownership")
    op.drop_index("ix_agent_runs_workflow_status", table_name="agent_runs")
    op.drop_table("agent_runs")
