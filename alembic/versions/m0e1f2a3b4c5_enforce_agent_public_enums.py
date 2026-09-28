"""Normalize and enforce M0 public enum ownership.

Revision ID: m0e1f2a3b4c5
Revises: m0d1e2f3a4b5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "m0e1f2a3b4c5"
down_revision: str | tuple[str, ...] | None = "m0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUSES = (
    "created",
    "running",
    "awaiting_user_input",
    "awaiting_confirmation",
    "recovery_required",
    "completed",
    "partial",
    "failed",
    "rejected",
    "cancelled",
    "cancelled_after_commit",
)


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    allowed = _sql_values(RUN_STATUSES)
    op.execute(
        sa.text(
            "UPDATE agent_runs SET workflow_status='recovery_required', "
            "reason_code='legacy_status_unrecognized' "
            f"WHERE workflow_status NOT IN ({allowed})"
        )
    )
    with op.batch_alter_table("agent_runs") as batch:
        batch.create_check_constraint(
            "ck_agent_run_public_status", f"workflow_status IN ({allowed})"
        )
        batch.create_check_constraint(
            "ck_agent_run_structured_identity",
            "is_legacy OR (research_context_id IS NOT NULL AND task_request_id IS NOT NULL "
            "AND agent_type IN ('A1','A2','A3','A4','A5') "
            "AND run_mode IN ('standalone_confirmation','composite_workflow'))",
        )
        batch.create_check_constraint("ck_agent_run_revision_positive", "revision >= 1")
    with op.batch_alter_table("agent_task_requests") as batch:
        batch.create_check_constraint(
            "ck_agent_task_requested_agent",
            "requested_agent IN ('A1','A2','A3','A4','A5')",
        )
    with op.batch_alter_table("agent_steps") as batch:
        batch.create_check_constraint(
            "ck_agent_step_public_status",
            "status IN ('created','running','awaiting_user_input',"
            "'awaiting_confirmation','completed','failed','cancelled','skipped')",
        )
        batch.create_check_constraint("ck_agent_step_attempt_positive", "attempt >= 1")
        batch.create_check_constraint(
            "ck_agent_step_revision_positive", "revision >= 1"
        )
    with op.batch_alter_table("agent_artifacts") as batch:
        batch.create_check_constraint(
            "ck_agent_artifact_validity_status",
            "validity_status IN ('valid','needs_revalidation','stale','superseded','invalid')",
        )
    with op.batch_alter_table("user_confirmations") as batch:
        batch.create_check_constraint(
            "ck_user_confirmation_status",
            "status IN ('pending','consumed','rejected','cancelled','expired','superseded')",
        )
        batch.create_check_constraint(
            "ck_user_confirmation_revision_positive", "revision >= 1"
        )
    with op.batch_alter_table("model_transfer_authorizations") as batch:
        batch.create_check_constraint(
            "ck_model_authorization_status",
            "status IN ('active','revoked','expired','consumed')",
        )
        batch.create_check_constraint(
            "ck_model_authorization_payload_shape",
            "payload_shape IN ('single_item','multi_item_bundle')",
        )
        batch.create_check_constraint(
            "ck_model_authorization_content_transform",
            "content_transform IN ('raw','deidentified','aggregated')",
        )
        batch.create_check_constraint(
            "ck_model_authorization_revision_positive", "revision >= 1"
        )


def downgrade() -> None:
    with op.batch_alter_table("model_transfer_authorizations") as batch:
        for name in (
            "ck_model_authorization_revision_positive",
            "ck_model_authorization_content_transform",
            "ck_model_authorization_payload_shape",
            "ck_model_authorization_status",
        ):
            batch.drop_constraint(name, type_="check")
    with op.batch_alter_table("user_confirmations") as batch:
        batch.drop_constraint("ck_user_confirmation_revision_positive", type_="check")
        batch.drop_constraint("ck_user_confirmation_status", type_="check")
    with op.batch_alter_table("agent_artifacts") as batch:
        batch.drop_constraint("ck_agent_artifact_validity_status", type_="check")
    with op.batch_alter_table("agent_steps") as batch:
        batch.drop_constraint("ck_agent_step_revision_positive", type_="check")
        batch.drop_constraint("ck_agent_step_attempt_positive", type_="check")
        batch.drop_constraint("ck_agent_step_public_status", type_="check")
    with op.batch_alter_table("agent_task_requests") as batch:
        batch.drop_constraint("ck_agent_task_requested_agent", type_="check")
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_constraint("ck_agent_run_revision_positive", type_="check")
        batch.drop_constraint("ck_agent_run_structured_identity", type_="check")
        batch.drop_constraint("ck_agent_run_public_status", type_="check")
