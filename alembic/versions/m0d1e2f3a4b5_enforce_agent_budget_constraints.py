"""Enforce M0 budget invariants in the database.

Revision ID: m0d1e2f3a4b5
Revises: m0c1d2e3f4a5
"""

from collections.abc import Sequence

from alembic import op


revision: str = "m0d1e2f3a4b5"
down_revision: str | tuple[str, ...] | None = "m0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COUNTERS = (
    "model_attempts",
    "input_tokens",
    "output_tokens",
    "retrieval_http",
    "total_http",
    "tool_calls",
)

ROOT_NONNEGATIVE = (
    tuple(f"max_{name}" for name in COUNTERS)
    + ("max_active_seconds",)
    + tuple(
        f"{prefix}_{name}" for name in COUNTERS for prefix in ("reserved", "settled")
    )
)


def upgrade() -> None:
    with op.batch_alter_table("agent_root_budgets") as batch:
        for column in ROOT_NONNEGATIVE:
            batch.create_check_constraint(
                f"ck_root_budget_{column}_nonnegative", f"{column} >= 0"
            )
        for name in COUNTERS:
            batch.create_check_constraint(
                f"ck_root_budget_{name}_within_limit",
                f"reserved_{name} + settled_{name} <= max_{name}",
            )

    with op.batch_alter_table("agent_budget_reservations") as batch:
        batch.create_check_constraint(
            "ck_budget_reservation_attempt_positive", "attempt >= 1"
        )
        batch.create_check_constraint(
            "ck_budget_reservation_status",
            "status IN ('active', 'settled', 'released')",
        )
        for name in COUNTERS:
            batch.create_check_constraint(
                f"ck_budget_reservation_{name}_bounds",
                f"reserved_{name} >= 0 AND actual_{name} >= 0 "
                f"AND actual_{name} <= reserved_{name}",
            )


def downgrade() -> None:
    with op.batch_alter_table("agent_budget_reservations") as batch:
        for name in reversed(COUNTERS):
            batch.drop_constraint(f"ck_budget_reservation_{name}_bounds", type_="check")
        batch.drop_constraint("ck_budget_reservation_status", type_="check")
        batch.drop_constraint("ck_budget_reservation_attempt_positive", type_="check")

    with op.batch_alter_table("agent_root_budgets") as batch:
        for name in reversed(COUNTERS):
            batch.drop_constraint(f"ck_root_budget_{name}_within_limit", type_="check")
        for column in reversed(ROOT_NONNEGATIVE):
            batch.drop_constraint(f"ck_root_budget_{column}_nonnegative", type_="check")
