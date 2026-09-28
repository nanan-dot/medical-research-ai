"""Typed HTTP contracts for recommendation V5."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.literature_search.schema import CitationItem

RunStatus = Literal["queued", "running", "active", "failed", "cancelled", "superseded"]
Mode = Literal["balanced", "latest", "key_evidence"]


class QueryTermRead(BaseModel):
    value: str
    dimension: str
    source: str
    field: str


class IncrementalBaselineRead(BaseModel):
    source_result_count: int
    publication_type_counts: dict[str, int]
    intent_concept_counts: dict[str, dict[str, int]]


class RunErrorRead(BaseModel):
    code: str
    message: str
    provider: str | None = None


class RecommendationRunCreate(BaseModel):
    intent_snapshot_id: int | None = Field(default=None, gt=0)
    exploration_query: str | None = Field(default=None, min_length=1, max_length=4000)
    mode: Mode = "balanced"
    candidate_count: int = Field(default=10, ge=1, le=100)
    retry_failed: bool = False
    force_refresh: bool = False


class RecommendationRunRead(BaseModel):
    run_id: int
    status: RunStatus
    operation: Literal["created", "reused"] = "reused"
    active_run_id: int | None = None
    mode: Mode
    candidate_count: int
    expected_count: int
    completed_count: int
    covered_count: int
    algorithm_version: str
    feature_schema_version: str
    intent_snapshot_id: int | None
    exploration_query: str | None = None
    narration_status: str = "not_requested"
    source_result_id: int
    source_score_generation_id: int | None = None
    last_error: RunErrorRead | None = None
    warnings: list[str] = Field(default_factory=list)
    pubmed_query: str | None = None
    pubmed_total_count: int | None = None
    collected_at: datetime | None = None
    query_terms: list[QueryTermRead] = Field(default_factory=list)
    incremental_baseline: IncrementalBaselineRead | None = None
    created_at: datetime
    activated_at: datetime | None = None


class RecommendationStatusRead(BaseModel):
    building: RecommendationRunRead | None
    active: RecommendationRunRead | None
    can_retry: bool


class MatchEvidence(BaseModel):
    dimension: str
    status: str
    matched_terms: list[str] = Field(default_factory=list)
    source: str
    field: str
    reason: str
    version: str
    excerpt: str | None = None


class Limitation(BaseModel):
    code: str
    message: str


class RecommendationReason(BaseModel):
    headline: str
    narrative: str
    relevance: str | None = None
    limitation: str | None = None
    display_source: Literal["base", "polished"] = "base"
    matches: list[MatchEvidence]
    incremental_value: str | None
    evidence_sources: list[str]
    limitations: list[Limitation]


class OverlapEvidence(BaseModel):
    collection: str
    match: str


class OpenSignalRead(BaseModel):
    source: Literal["openalex"] = "openalex"
    status: str = "not_requested"
    cited_by_count: int | None = None
    counts_by_year: dict[int, int] = Field(default_factory=dict)
    score: float | None = None


class DecisionRead(BaseModel):
    decision: Literal["pending", "accepted", "dismissed"]
    dismiss_reason: (
        Literal["duplicate", "off_topic", "unsuitable_study_type", "other"] | None
    ) = None


class RecommendationItemRead(BaseModel):
    pmid: str
    citation: CitationItem
    priority_score: float | None
    relevance_score: float | None
    incremental_value_score: float | None
    evidence_fit_score: float | None
    recency_score: float | None
    overlap_status: str
    overlap_evidence: list[OverlapEvidence]
    open_signal: OpenSignalRead
    reason: RecommendationReason
    rank: int
    decision: DecisionRead
    narration_status: str = "not_requested"


class RecommendationPage(BaseModel):
    research_context_id: int
    research_name: str
    source_result_id: int
    intent_snapshot_id: int | None
    exploration_query: str | None = None
    run_id: int
    mode: Mode
    algorithm_version: str
    total: int
    novel_count: int
    covered_count: int
    page: int
    page_size: int
    items: list[RecommendationItemRead]


class DismissRequest(BaseModel):
    reason: Literal["duplicate", "off_topic", "unsuitable_study_type", "other"]
