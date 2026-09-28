"""add recommendation v5

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | Sequence[str] | None = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "research_context_id",
            sa.Integer(),
            sa.ForeignKey("research_contexts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intent_snapshot_id",
            sa.Integer(),
            sa.ForeignKey(
                "literature_research_intent_snapshots.id", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "source_score_generation_id",
            sa.Integer(),
            sa.ForeignKey("literature_score_generations.id", ondelete="SET NULL"),
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("feature_schema_version", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("expected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("covered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "request_options_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("last_error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "source_result_id", "input_fingerprint", name="uq_recommendation_run_input"
        ),
    )
    op.create_index(
        "ix_recommendation_run_active",
        "recommendation_runs",
        ["source_result_id", "status"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "recommendation_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pmid", sa.Text(), nullable=False),
        sa.Column("citation_json", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float()),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("incremental_value_score", sa.Float()),
        sa.Column("evidence_fit_score", sa.Float()),
        sa.Column("recency_score", sa.Float()),
        sa.Column("open_signal_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("overlap_status", sa.Text(), nullable=False),
        sa.Column(
            "overlap_evidence_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("reason_headline", sa.Text(), nullable=False),
        sa.Column("reason_narrative", sa.Text(), nullable=False),
        sa.Column(
            "reason_matches_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("reason_incremental_value", sa.Text()),
        sa.Column(
            "evidence_sources_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "run_id", "pmid", name="uq_recommendation_candidate_run_pmid"
        ),
    )
    op.create_index(
        "ix_recommendation_candidates_run_id", "recommendation_candidates", ["run_id"]
    )
    op.create_table(
        "recommendation_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pmid", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("dismiss_reason", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "run_id", "pmid", name="uq_recommendation_decision_run_pmid"
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_decisions")
    op.drop_index(
        "ix_recommendation_candidates_run_id", table_name="recommendation_candidates"
    )
    op.drop_table("recommendation_candidates")
    op.drop_index("ix_recommendation_run_active", table_name="recommendation_runs")
    op.drop_table("recommendation_runs")
