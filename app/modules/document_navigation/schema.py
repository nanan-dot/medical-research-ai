"""Contracts for evidence-bound local RAG navigation."""

from enum import StrEnum

from pydantic import BaseModel, Field


class NavigationStrategy(StrEnum):
    HYBRID = "hybrid"
    BM25 = "bm25"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    NOT_REQUESTED = "not_requested"


class DocumentNavigationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    knowledge_source_id: int | None = Field(default=None, gt=0)
    indexed_only: bool = True
    limit: int = Field(default=10, ge=1, le=30)


class NavigationCondition(BaseModel):
    label: str
    status: VerificationStatus
    reason: str


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
    condition_status: list[NavigationCondition] = Field(default_factory=list)


class DocumentNavigationResponse(BaseModel):
    query: str
    knowledge_source_id: int | None
    indexed_only: bool
    searchable_document_count: int = Field(ge=0)
    strategy: NavigationStrategy
    fallback_reason: str | None = None
    conditions: list[NavigationCondition] = Field(default_factory=list)
    results: list[DocumentNavigationResult]
