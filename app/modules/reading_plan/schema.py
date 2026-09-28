"""Pydantic v2 HTTP contracts for reading plans."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Stage = Literal["overview", "clinical_decision", "primary_evidence", "frontier"]
Role = Literal["core", "candidate"]


class PlanGenerateRequest(BaseModel):
    target_core_count: int = Field(default=12, ge=10, le=20)
    duplicate_mode: Literal["all", "consolidated"] = "all"
    preserve: bool = True


class PlanItemPatch(BaseModel):
    stage: Stage | None = None
    role: Role | None = None
    stage_order: int | None = Field(default=None, ge=0)
    is_locked: bool | None = None


class ManualItemCreate(BaseModel):
    pmid: str = Field(min_length=1, max_length=20)
    stage: Stage = "frontier"
    role: Role = "candidate"
    is_locked: bool = False


class StageOrderRequest(BaseModel):
    pmids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_pmids(self) -> "StageOrderRequest":
        if len(self.pmids) != len(set(self.pmids)):
            raise ValueError("pmids must not contain duplicates")
        return self


class PromoteCoreRequest(BaseModel):
    pmid: str = Field(min_length=1, max_length=20)
    strategy: Literal["expand", "replace"] | None = None
    replace_pmid: str | None = None

    @model_validator(mode="after")
    def replacement_is_explicit(self) -> "PromoteCoreRequest":
        if self.strategy == "replace" and not self.replace_pmid:
            raise ValueError("replace_pmid is required for replace")
        return self


class PlanItemRead(BaseModel):
    pmid: str
    doi: str | None
    title: str | None
    authors: list[str]
    journal: str | None
    year: int | None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publication_types: list[str]
    abstract_status: str
    journal_metrics: dict[str, object | None]
    article_score: dict[str, object | None]
    recommendation_reason: str
    reading_reason: "ReadingReasonRead"
    evidence_features: dict[str, object]
    limitations: list[str]
    read_status: Literal["unread", "read"]
    read_at: datetime | None
    is_key: bool
    is_locked: bool
    source: Literal["system", "manual"]
    stage: Stage
    role: Role
    stage_order: int
    pubmed_url: str


class ReadingReasonRead(BaseModel):
    headline: str
    narrative: str
    stage_fit: list[str]
    research_question_matches: list[str]
    incremental_value: list[str]
    evidence_sources: list[str]
    limitations: list[str]
    generation_method: Literal["deterministic", "llm_grounded"]
    status: Literal["complete", "partial"]


class StageRead(BaseModel):
    stage: Stage
    core_count: int
    candidate_count: int
    read_count: int
    core: list[PlanItemRead]


class ReadingPlanRead(BaseModel):
    id: int
    version: int
    status: Literal["draft", "active", "archived"]
    algorithm_version: str
    result_id: int
    generated_at: datetime
    activated_at: datetime | None
    duplicate_mode: Literal["all", "consolidated"]
    target_core_count: int
    generation_basis: dict[str, object]
    limitations: list[str]
    total_core_count: int
    read_count: int
    unread_count: int
    progress_percent: float
    stages: list[StageRead]


class CandidatePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PlanItemRead]


class ReadingPlanVersionSummary(BaseModel):
    id: int
    version: int
    status: Literal["draft", "active", "archived"]
    algorithm_version: str
    generated_at: datetime
    activated_at: datetime | None
    target_core_count: int
    duplicate_mode: Literal["all", "consolidated"]
    total_core_count: int
    read_count: int


class ReadingPlanVersionPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReadingPlanVersionSummary]
