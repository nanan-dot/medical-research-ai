"""Contracts for evidence-bound local RAG navigation."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class NavigationStrategy(StrEnum):
    HYBRID = "hybrid"
    BM25 = "bm25"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    NOT_REQUESTED = "not_requested"


class ConditionMatchStatus(StrEnum):
    """Distinguish trusted metadata facts from unstructured text mentions."""

    METADATA_MATCH = "metadata_match"
    METADATA_MISMATCH = "metadata_mismatch"
    TEXT_MENTION = "text_mention"
    NOT_ASSESSED = "not_assessed"


class DocumentNavigationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    knowledge_source_id: int | None = Field(default=None, gt=0)
    indexed_only: bool = True
    limit: int = Field(default=10, ge=1, le=30)


class NavigationCondition(BaseModel):
    label: str
    status: VerificationStatus
    reason: str
    condition_id: str = ""
    field: str | None = None
    expected_value: str | None = None


class NavigationConditionMatch(BaseModel):
    condition_id: str
    label: str
    status: ConditionMatchStatus
    basis: Literal["metadata", "text", "none"]
    reason: str
    source_field: str | None = None
    evidence_span: str | None = None


class NavigationBudget(BaseModel):
    dense_top_k: int = Field(ge=1)
    sparse_top_k: int = Field(ge=1)
    fusion_top_k: int = Field(ge=1)
    rerank_candidate_top_k: int = Field(ge=1)
    requested_limit: int = Field(ge=1)
    candidate_limit: int = Field(ge=0)
    final_limit: int = Field(ge=0)
    status: Literal["within_budget", "limited"]


class NavigationLocation(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None


class DocumentNavigationResult(BaseModel):
    document_id: int
    title: str
    filename: str
    knowledge_source_id: int
    knowledge_source_name: str
    relative_path: str
    match_reason: str
    location: NavigationLocation
    excerpt: str
    retrieval_score: float | None = None
    rerank_score: float | None = None
    condition_status: list[NavigationCondition] = Field(default_factory=list)
    condition_matches: list[NavigationConditionMatch] = Field(default_factory=list)


class DocumentNavigationResponse(BaseModel):
    query: str
    knowledge_source_id: int | None
    indexed_only: bool
    effective_indexed_only: bool = True
    searchable_document_count: int = Field(ge=0)
    strategy: NavigationStrategy
    fallback_reason: str | None = None
    rerank_status: Literal["disabled", "applied", "fallback", "empty"] = "disabled"
    rerank_reason_code: Literal[
        "disabled",
        "applied",
        "no_candidates",
        "model_unavailable",
        "model_busy",
        "timeout",
        "inference_error",
    ] = "disabled"
    candidate_budget: NavigationBudget | None = None
    trace_id: str | None = None
    conditions: list[NavigationCondition] = Field(default_factory=list)
    results: list[DocumentNavigationResult]
