"""Enforce all frozen M0 budget counters in the database.

Revision ID: m0h1c2d3e4f5
Revises: m0g1b2c3d4e5
"""

from collections.abc import Sequence

from alembic import op

revision: str = "m0h1c2d3e4f5"
down_revision: str | Sequence[str] | None = "m0g1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_COUNTERS = ("model_http_attempts", "other_http_attempts", "active_seconds")


def upgrade() -> None:
    # Before M0g, total HTTP held model attempts that were not categorized.
    op.execute(
        "UPDATE agent_root_budgets SET "
        "max_model_http_attempts = MAX(max_total_http - max_retrieval_http, 0), "
        "reserved_model_http_attempts = MAX(reserved_total_http - reserved_retrieval_http, 0), "
        "settled_model_http_attempts = MAX(settled_total_http - settled_retrieval_http, 0)"
    )
    op.execute(
        "UPDATE agent_budget_reservations SET "
        "reserved_model_http_attempts = MAX(reserved_total_http - reserved_retrieval_http, 0), "
        "actual_model_http_attempts = MAX(actual_total_http - actual_retrieval_http, 0)"
    )

    with op.batch_alter_table("agent_root_budgets") as batch:
        for name in NEW_COUNTERS:
            for prefix in ("max", "reserved", "settled"):
                if name == "active_seconds" and prefix == "max":
                    continue
                column = f"{prefix}_{name}"
                batch.create_check_constraint(
                    f"ck_root_budget_{column}_nonnegative", f"{column} >= 0"
                )
            batch.create_check_constraint(
                f"ck_root_budget_{name}_within_limit",
                f"reserved_{name} + settled_{name} <= max_{name}",
            )
        batch.create_check_constraint(
            "ck_root_budget_reserved_http_conservation",
            "reserved_total_http = reserved_retrieval_http + "
            "reserved_model_http_attempts + reserved_other_http_attempts",
        )
        batch.create_check_constraint(
            "ck_root_budget_settled_http_conservation",
            "settled_total_http = settled_retrieval_http + "
            "settled_model_http_attempts + settled_other_http_attempts",
        )

    with op.batch_alter_table("agent_budget_reservations") as batch:
        for name in NEW_COUNTERS:
            batch.create_check_constraint(
                f"ck_budget_reservation_{name}_bounds",
                f"reserved_{name} >= 0 AND actual_{name} >= 0 "
                f"AND actual_{name} <= reserved_{name}",
            )
        batch.create_check_constraint(
            "ck_budget_reservation_reserved_http_conservation",
            "reserved_total_http = reserved_retrieval_http + "
            "reserved_model_http_attempts + reserved_other_http_attempts",
        )
        batch.create_check_constraint(
            "ck_budget_reservation_actual_http_conservation",
            "actual_total_http = actual_retrieval_http + "
            "actual_model_http_attempts + actual_other_http_attempts",
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_budget_reservations") as batch:
        batch.drop_constraint(
            "ck_budget_reservation_actual_http_conservation", type_="check"
        )
        batch.drop_constraint(
            "ck_budget_reservation_reserved_http_conservation", type_="check"
        )
        for name in reversed(NEW_COUNTERS):
            batch.drop_constraint(f"ck_budget_reservation_{name}_bounds", type_="check")

    with op.batch_alter_table("agent_root_budgets") as batch:
        batch.drop_constraint("ck_root_budget_settled_http_conservation", type_="check")
        batch.drop_constraint(
            "ck_root_budget_reserved_http_conservation", type_="check"
        )
        for name in reversed(NEW_COUNTERS):
            batch.drop_constraint(f"ck_root_budget_{name}_within_limit", type_="check")
            for prefix in reversed(("max", "reserved", "settled")):
                if name == "active_seconds" and prefix == "max":
                    continue
                batch.drop_constraint(
                    f"ck_root_budget_{prefix}_{name}_nonnegative", type_="check"
                )
