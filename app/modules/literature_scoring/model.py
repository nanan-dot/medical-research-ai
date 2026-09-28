"""Persistent scoring generations; search snapshots remain immutable."""

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


class LiteratureScoreGeneration(Base):
    """A complete scoring run that can be atomically published for one result."""

    __tablename__ = "literature_score_generations"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "input_fingerprint",
            name="uq_literature_score_generation_fingerprint",
        ),
        Index(
            "ix_literature_score_generation_active",
            "result_id",
            "status",
            "activated_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("literature_search_results.id", ondelete="CASCADE"), nullable=False
    )
    intent_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("literature_research_intent_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    expected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    request_options_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class LiteratureArticleScore(Base):
    """Scores and evidence for one PMID within exactly one generation."""

    __tablename__ = "literature_article_scores"
    __table_args__ = (
        UniqueConstraint(
            "generation_id", "pmid", name="uq_literature_article_score_generation_pmid"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    generation_id: Mapped[int] = mapped_column(
        ForeignKey("literature_score_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pmid: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="not_scored"
    )
    relevance_score: Mapped[float | None] = mapped_column(nullable=True)
    relevance_confidence: Mapped[float | None] = mapped_column(nullable=True)
    evidence_fit_score: Mapped[float | None] = mapped_column(nullable=True)
    article_impact_score: Mapped[float | None] = mapped_column(nullable=True)
    popularity_score: Mapped[float | None] = mapped_column(nullable=True)
    classic_score: Mapped[float | None] = mapped_column(nullable=True)
    recency_score: Mapped[float | None] = mapped_column(nullable=True)
    priority_score: Mapped[float | None] = mapped_column(nullable=True)
    cited_by_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    citation_metrics_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    score_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="unavailable"
    )
    components_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class LiteratureResearchIntentSnapshot(Base):
    """Immutable, user-confirmed research intent used by formal scoring."""

    __tablename__ = "literature_research_intent_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "research_context_id",
            "fingerprint",
            name="uq_literature_intent_context_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_context_id: Mapped[int] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False
    )
    confirmation_status: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions_json: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
