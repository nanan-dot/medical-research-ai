"""Persistent V5 recommendation runs, candidates, and user decisions."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"
    __table_args__ = (
        UniqueConstraint(
            "source_result_id", "input_fingerprint", name="uq_recommendation_run_input"
        ),
        Index(
            "ix_recommendation_run_active",
            "source_result_id",
            "status",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_context_id: Mapped[int] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False
    )
    source_result_id: Mapped[int] = mapped_column(
        ForeignKey("literature_search_results.id", ondelete="CASCADE"), nullable=False
    )
    intent_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("literature_research_intent_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_score_generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("literature_score_generations.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    expected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    covered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    request_options_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class RecommendationCandidate(Base):
    __tablename__ = "recommendation_candidates"
    __table_args__ = (
        UniqueConstraint("run_id", "pmid", name="uq_recommendation_candidate_run_pmid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pmid: Mapped[str] = mapped_column(Text, nullable=False)
    citation_json: Mapped[str] = mapped_column(Text, nullable=False)
    priority_score: Mapped[float | None] = mapped_column()
    relevance_score: Mapped[float | None] = mapped_column()
    incremental_value_score: Mapped[float | None] = mapped_column()
    evidence_fit_score: Mapped[float | None] = mapped_column()
    recency_score: Mapped[float | None] = mapped_column()
    open_signal_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    overlap_status: Mapped[str] = mapped_column(Text, nullable=False)
    overlap_evidence_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    reason_headline: Mapped[str] = mapped_column(Text, nullable=False)
    reason_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    reason_matches_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reason_incremental_value: Mapped[str | None] = mapped_column(Text)
    evidence_sources_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # Keep deterministic evidence separate from optional model wording so a failed
    # narrator can never erase the reason users were already shown.
    base_reason_json: Mapped[str | None] = mapped_column(Text)
    reason_fact_packet_json: Mapped[str | None] = mapped_column(Text)
    polished_reason_json: Mapped[str | None] = mapped_column(Text)
    display_reason_source: Mapped[str] = mapped_column(Text, nullable=False, default="base")
    narration_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_requested")
    narration_model: Mapped[str | None] = mapped_column(Text)
    narration_error_code: Mapped[str | None] = mapped_column(Text)
    narration_fingerprint: Mapped[str | None] = mapped_column(Text)
    polished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class RecommendationDecision(Base):
    __tablename__ = "recommendation_decisions"
    __table_args__ = (
        UniqueConstraint("run_id", "pmid", name="uq_recommendation_decision_run_pmid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False
    )
    pmid: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    dismiss_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class RecommendationNarrationLease(Base):
    """Cross-run lease/cache that makes model narration idempotent by fact packet."""

    __tablename__ = "recommendation_narration_leases"

    fingerprint: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    claim_token: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    polished_reason_json: Mapped[str | None] = mapped_column(Text)
    narration_model: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
