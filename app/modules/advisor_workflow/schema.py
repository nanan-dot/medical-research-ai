"""Contracts for advisor review records and immutable direction revisions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["accept", "revise", "reject"]
ReviewerType = Literal["real", "mock"]
Severity = Literal["blocker", "major", "minor"]
ItemStatus = Literal["pending", "done"]
Provider = Literal["ollama", "openai", "openrouter"]


class ReviewPoint(BaseModel):
    field_name: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2000)
    severity: Severity


class LiteratureGap(BaseModel):
    statement: str = Field(min_length=1, max_length=2000)
    source_gap: str = Field(min_length=1, max_length=1000)
    search_terms: str = Field(min_length=1, max_length=2000)
    status: ItemStatus = "pending"


class ExperimentCondition(BaseModel):
    condition: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=2000)
    status: ItemStatus = "pending"


class AdvisorNoteCreate(BaseModel):
    decision: Decision
    summary: str = Field(min_length=1, max_length=3000)
    points: list[ReviewPoint] = Field(min_length=1, max_length=30)
    literature_gaps: list[LiteratureGap] = Field(default_factory=list, max_length=30)
    experiment_conditions: list[ExperimentCondition] = Field(default_factory=list, max_length=30)


class MockReviewRequest(BaseModel):
    """云端模型必须同时显式指定 provider 与配置，避免隐私内容静默外发。"""

    provider: Provider | None = None
    model_config_id: int | None = Field(default=None, gt=0)


class AdvisorReviewRead(AdvisorNoteCreate):
    id: int
    direction_id: int
    reviewer_type: ReviewerType
    is_ai_simulation: bool
    created_at: datetime


class DirectionVersionRead(BaseModel):
    id: int | None
    direction_id: int
    version: int
    revision_parent_id: int | None
    snapshot: dict[str, object]
    created_at: datetime


class ReportRead(BaseModel):
    filename: str
    content: str
