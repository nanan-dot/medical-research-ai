"""Close M0 recovery, hierarchy and budget trust boundaries.

Revision ID: m0g1b2c3d4e5
Revises: m0f1a2b3c4d5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m0g1b2c3d4e5"
down_revision: str | Sequence[str] | None = "m0f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("root_run_id", sa.String(36), nullable=True))
    op.add_column(
        "agent_runs", sa.Column("parent_run_id", sa.String(36), nullable=True)
    )
    op.execute(
        sa.text("UPDATE agent_runs SET root_run_id = run_id WHERE is_legacy = 0")
    )
    op.create_index("ix_agent_runs_root_run_id", "agent_runs", ["root_run_id"])
    op.create_index("ix_agent_runs_parent_run_id", "agent_runs", ["parent_run_id"])

    for name in ("model_http_attempts", "other_http_attempts"):
        op.add_column(
            "agent_root_budgets",
            sa.Column(f"max_{name}", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "agent_root_budgets",
            sa.Column(
                f"reserved_{name}", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        op.add_column(
            "agent_root_budgets",
            sa.Column(
                f"settled_{name}", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        op.add_column(
            "agent_budget_reservations",
            sa.Column(
                f"reserved_{name}", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        op.add_column(
            "agent_budget_reservations",
            sa.Column(
                f"actual_{name}", sa.Integer(), nullable=False, server_default="0"
            ),
        )
    op.add_column(
        "agent_root_budgets",
        sa.Column(
            "reserved_active_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "agent_root_budgets",
        sa.Column(
            "settled_active_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "agent_budget_reservations",
        sa.Column(
            "reserved_active_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "agent_budget_reservations",
        sa.Column(
            "actual_active_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    op.create_table(
        "agent_external_executions",
        sa.Column("execution_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("step_id", sa.String(64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("authorization_id", sa.String(64), nullable=False),
        sa.Column("reservation_id", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("result_payload_hash", sa.String(64), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "step_id", "attempt", name="uq_external_execution_step_attempt"
        ),
        sa.CheckConstraint(
            "state IN ('prepared','sent','succeeded','failed_before_send','outcome_unknown')",
            name="ck_agent_external_execution_state",
        ),
    )
    op.create_index(
        "ix_external_executions_run", "agent_external_executions", ["run_id"]
    )
    op.create_index(
        "ix_external_executions_step", "agent_external_executions", ["step_id"]
    )
    op.create_index(
        "ix_external_executions_state", "agent_external_executions", ["state"]
    )


def downgrade() -> None:
    op.drop_table("agent_external_executions")
    op.drop_column("agent_budget_reservations", "actual_active_seconds")
    op.drop_column("agent_budget_reservations", "reserved_active_seconds")
    op.drop_column("agent_root_budgets", "settled_active_seconds")
    op.drop_column("agent_root_budgets", "reserved_active_seconds")
    for name in reversed(("model_http_attempts", "other_http_attempts")):
        op.drop_column("agent_budget_reservations", f"actual_{name}")
        op.drop_column("agent_budget_reservations", f"reserved_{name}")
        op.drop_column("agent_root_budgets", f"settled_{name}")
        op.drop_column("agent_root_budgets", f"reserved_{name}")
        op.drop_column("agent_root_budgets", f"max_{name}")
    op.drop_index("ix_agent_runs_parent_run_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_root_run_id", table_name="agent_runs")
    op.drop_column("agent_runs", "parent_run_id")
    op.drop_column("agent_runs", "root_run_id")
