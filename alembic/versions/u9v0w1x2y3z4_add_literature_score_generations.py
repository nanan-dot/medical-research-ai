"""add literature scoring generations

Revision ID: u9v0w1x2y3z4
Revises: s7t8u9v0w1x2
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "u9v0w1x2y3z4"
down_revision: str | None = "s7t8u9v0w1x2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "literature_score_generations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("literature_search_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("intent_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("feature_schema_version", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("expected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "result_id",
            "input_fingerprint",
            name="uq_literature_score_generation_fingerprint",
        ),
    )
    op.create_index(
        "ix_literature_score_generation_active",
        "literature_score_generations",
        ["result_id", "status", "activated_at"],
    )
    op.create_table(
        "literature_article_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "generation_id",
            sa.Integer(),
            sa.ForeignKey("literature_score_generations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pmid", sa.Text(), nullable=False),
        sa.Column("eligibility_status", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("relevance_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_fit_score", sa.Float(), nullable=True),
        sa.Column("article_impact_score", sa.Float(), nullable=True),
        sa.Column("popularity_score", sa.Float(), nullable=True),
        sa.Column("classic_score", sa.Float(), nullable=True),
        sa.Column("recency_score", sa.Float(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("cited_by_count", sa.Integer(), nullable=True),
        sa.Column("citation_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score_status", sa.Text(), nullable=False),
        sa.Column("components_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "generation_id", "pmid", name="uq_literature_article_score_generation_pmid"
        ),
    )
    op.create_index(
        "ix_literature_article_scores_generation_id",
        "literature_article_scores",
        ["generation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_literature_article_scores_generation_id",
        table_name="literature_article_scores",
    )
    op.drop_table("literature_article_scores")
    op.drop_index(
        "ix_literature_score_generation_active",
        table_name="literature_score_generations",
    )
    op.drop_table("literature_score_generations")
