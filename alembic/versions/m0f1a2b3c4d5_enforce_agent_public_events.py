"""Enforce the frozen M0 public event types.

Revision ID: m0f1a2b3c4d5
Revises: m0e1f2a3b4c5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "m0f1a2b3c4d5"
down_revision: str | tuple[str, ...] | None = "m0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENT_TYPES = (
    "run.created",
    "run.status_changed",
    "step.status_changed",
    "artifact.created",
    "artifact.invalidated",
    "confirmation.requested",
    "confirmation.recorded",
    "confirmation.superseded",
    "budget.reserved",
    "budget.settled",
    "export.prepared",
    "export.completed",
    "error.raised",
)


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    event_types = _sql_values(EVENT_TYPES)
    op.execute(
        sa.text(
            "UPDATE agent_events SET event_type='error.raised' "
            f"WHERE event_type NOT IN ({event_types})"
        )
    )
    with op.batch_alter_table("agent_events") as batch:
        batch.create_check_constraint(
            "ck_agent_event_public_type", f"event_type IN ({event_types})"
        )
        batch.create_check_constraint("ck_agent_event_seq_positive", "seq >= 1")
    op.execute(
        sa.text(
            "UPDATE agent_outbox SET event_type='error.raised' "
            f"WHERE event_type NOT IN ({event_types})"
        )
    )
    with op.batch_alter_table("agent_outbox") as batch:
        batch.create_check_constraint(
            "ck_agent_outbox_public_type", f"event_type IN ({event_types})"
        )
        batch.create_check_constraint(
            "ck_agent_outbox_attempt_nonnegative", "attempt_count >= 0"
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_outbox") as batch:
        batch.drop_constraint("ck_agent_outbox_attempt_nonnegative", type_="check")
        batch.drop_constraint("ck_agent_outbox_public_type", type_="check")
    with op.batch_alter_table("agent_events") as batch:
        batch.drop_constraint("ck_agent_event_seq_positive", type_="check")
        batch.drop_constraint("ck_agent_event_public_type", type_="check")
