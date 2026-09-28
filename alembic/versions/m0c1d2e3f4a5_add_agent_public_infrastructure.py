"""add M0 public Agent infrastructure

Revision ID: m0c1d2e3f4a5
Revises: aa1b2c3d4e5f, u1chat20260904
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m0c1d2e3f4a5"
down_revision: str | Sequence[str] | None = ("aa1b2c3d4e5f", "u1chat20260904")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in (
        sa.Column("research_context_id", sa.String(64), nullable=True),
        sa.Column("task_request_id", sa.String(64), nullable=True),
        sa.Column("agent_type", sa.String(32), nullable=True),
        sa.Column("run_mode", sa.String(32), nullable=True),
        sa.Column("phase", sa.String(64), nullable=True),
        sa.Column("reason_code", sa.String(128), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_legacy", sa.Boolean(), nullable=False, server_default=sa.true()),
    ):
        op.add_column("agent_runs", column)
    op.create_index(
        "ix_agent_runs_research_context_id", "agent_runs", ["research_context_id"]
    )

    op.create_table(
        "agent_task_requests",
        sa.Column("task_request_id", sa.String(64), primary_key=True),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("requested_agent", sa.String(32), nullable=False),
        sa.Column("intent", sa.String(128), nullable=False),
        sa.Column("input_artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("authorization_refs_json", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_agent_task_requests_context", "agent_task_requests", ["research_context_id"]
    )
    op.create_index(
        "ix_agent_task_requests_hash", "agent_task_requests", ["request_hash"]
    )

    op.create_table(
        "research_context_memberships",
        sa.Column("membership_id", sa.String(64), primary_key=True),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("membership_role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "research_context_id", "actor_scope", name="uq_context_actor_scope"
        ),
    )
    op.create_index(
        "ix_context_memberships_context",
        "research_context_memberships",
        ["research_context_id"],
    )
    op.execute(
        sa.text(
            "INSERT INTO research_context_memberships "
            "(membership_id, research_context_id, actor_scope, membership_role, status, created_at) "
            "SELECT 'migration-local-owner-' || CAST(id AS VARCHAR), CAST(id AS VARCHAR), "
            "'local-owner', 'owner', 'active', CURRENT_TIMESTAMP FROM research_contexts"
        )
    )

    op.create_table(
        "agent_role_qualifications",
        sa.Column("qualification_id", sa.String(64), primary_key=True),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("authorized_role", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(64), nullable=False),
        sa.Column("source_ref", sa.String(256), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_role_qualifications_actor", "agent_role_qualifications", ["actor_scope"]
    )

    op.create_table(
        "agent_steps",
        sa.Column("step_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("output_refs_json", sa.JSON(), nullable=False),
        sa.Column("expected_revision", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint(
            "run_id", "step_kind", "attempt", name="uq_agent_step_attempt"
        ),
    )
    op.create_index("ix_agent_steps_run", "agent_steps", ["run_id"])
    op.create_index("ix_agent_steps_status", "agent_steps", ["status"])

    op.create_table(
        "agent_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("detail_kind", sa.String(64), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "seq", name="uq_agent_event_seq"),
    )
    op.create_index("ix_agent_events_run", "agent_events", ["run_id"])

    op.create_table(
        "agent_artifacts",
        sa.Column("artifact_id", sa.String(64), primary_key=True),
        sa.Column("artifact_type", sa.String(96), nullable=False),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("artifact_key", sa.String(128), nullable=False),
        sa.Column("version_key", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("validity_status", sa.String(32), nullable=False),
        sa.Column("typed_ref_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "research_context_id",
            "artifact_type",
            "artifact_key",
            "version_key",
            name="uq_artifact_version",
        ),
    )
    op.create_index("ix_artifacts_type", "agent_artifacts", ["artifact_type"])
    op.create_index("ix_artifacts_context", "agent_artifacts", ["research_context_id"])
    op.create_index("ix_artifacts_hash", "agent_artifacts", ["content_hash"])

    op.create_table(
        "artifact_dependencies",
        sa.Column("dependency_id", sa.String(64), primary_key=True),
        sa.Column(
            "downstream_artifact_id",
            sa.String(64),
            sa.ForeignKey("agent_artifacts.artifact_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "upstream_artifact_id",
            sa.String(64),
            sa.ForeignKey("agent_artifacts.artifact_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("upstream_version_key", sa.String(128), nullable=False),
        sa.Column("upstream_content_hash", sa.String(64), nullable=False),
        sa.Column("dependency_kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "downstream_artifact_id",
            "upstream_artifact_id",
            "upstream_version_key",
            name="uq_artifact_dependency",
        ),
    )
    op.create_index(
        "ix_dependencies_downstream",
        "artifact_dependencies",
        ["downstream_artifact_id"],
    )
    op.create_index(
        "ix_dependencies_upstream", "artifact_dependencies", ["upstream_artifact_id"]
    )

    op.create_table(
        "agent_idempotency_records",
        sa.Column("idempotency_id", sa.String(64), primary_key=True),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("resource_version", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "research_context_id",
            "actor_scope",
            "action",
            "idempotency_key",
            name="uq_agent_idempotency",
        ),
    )

    op.create_table(
        "user_confirmations",
        sa.Column("confirmation_id", sa.String(64), primary_key=True),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_refs_json", sa.JSON(), nullable=False),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("expected_revisions_json", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_confirmation_context", "user_confirmations", ["research_context_id"]
    )
    op.create_index("ix_confirmation_status", "user_confirmations", ["status"])
    op.create_index(
        "uq_pending_confirmation_binding",
        "user_confirmations",
        ["research_context_id", "actor_scope", "action", "binding_hash"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "role_decisions",
        sa.Column("decision_id", sa.String(64), primary_key=True),
        sa.Column("version_id", sa.String(64), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("confirmation_id", sa.String(64), nullable=False),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("authorized_role", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("target_refs_json", sa.JSON(), nullable=False),
        sa.Column("target_binding_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "model_transfer_authorizations",
        sa.Column("authorization_id", sa.String(64), primary_key=True),
        sa.Column("research_context_id", sa.String(64), nullable=False),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("provider_scope", sa.String(128), nullable=False),
        sa.Column("model_scope", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("content_granularity", sa.String(32), nullable=False),
        sa.Column("data_categories_json", sa.JSON(), nullable=False),
        sa.Column("payload_refs_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_shape", sa.String(32), nullable=False),
        sa.Column("content_transform", sa.String(32), nullable=False),
        sa.Column(
            "allow_cloud_transfer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_model_auth_context",
        "model_transfer_authorizations",
        ["research_context_id"],
    )
    op.create_index("ix_model_auth_status", "model_transfer_authorizations", ["status"])

    op.create_table(
        "agent_root_budgets",
        sa.Column("budget_id", sa.String(64), primary_key=True),
        sa.Column("root_run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("max_model_attempts", sa.Integer(), nullable=False),
        sa.Column("max_input_tokens", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("max_retrieval_http", sa.Integer(), nullable=False),
        sa.Column("max_total_http", sa.Integer(), nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False),
        sa.Column("max_active_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "reserved_model_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_model_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_retrieval_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_retrieval_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_total_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_total_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_tool_calls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "settled_tool_calls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "agent_budget_reservations",
        sa.Column("reservation_id", sa.String(64), primary_key=True),
        sa.Column("budget_id", sa.String(64), nullable=False),
        sa.Column("child_run_id", sa.String(64), nullable=False),
        sa.Column("step_id", sa.String(64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column(
            "reserved_model_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_model_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_retrieval_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_retrieval_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_total_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_total_http", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_tool_calls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_tool_calls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("step_id", "attempt", name="uq_budget_step_attempt"),
    )
    op.create_index(
        "ix_budget_reservations_budget", "agent_budget_reservations", ["budget_id"]
    )

    op.create_table(
        "invalidation_records",
        sa.Column("invalidation_id", sa.String(64), primary_key=True),
        sa.Column("target_artifact_id", sa.String(64), nullable=False),
        sa.Column("upstream_artifact_id", sa.String(64), nullable=True),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("old_content_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_invalidations_target", "invalidation_records", ["target_artifact_id"]
    )

    op.create_table(
        "agent_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
    )
    op.create_index("ix_agent_outbox_unpublished", "agent_outbox", ["published_at"])


def downgrade() -> None:
    for table in (
        "agent_outbox",
        "invalidation_records",
        "agent_budget_reservations",
        "agent_root_budgets",
        "model_transfer_authorizations",
        "role_decisions",
        "user_confirmations",
        "agent_idempotency_records",
        "artifact_dependencies",
        "agent_artifacts",
        "agent_events",
        "agent_steps",
        "agent_role_qualifications",
        "research_context_memberships",
        "agent_task_requests",
    ):
        op.drop_table(table)
    op.drop_index("ix_agent_runs_research_context_id", table_name="agent_runs")
    for name in (
        "is_legacy",
        "completed_at",
        "started_at",
        "cancel_requested_at",
        "revision",
        "reason_code",
        "phase",
        "run_mode",
        "agent_type",
        "task_request_id",
        "research_context_id",
    ):
        op.drop_column("agent_runs", name)
