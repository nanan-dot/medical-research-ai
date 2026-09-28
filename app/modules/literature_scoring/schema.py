"""Public contracts for persisted literature scoring work."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ScoringRunStatus = Literal[
    "not_started",
    "queued",
    "collecting_inputs",
    "scoring",
    "validating",
    "active",
    "failed",
]


class ScoringRunCreate(BaseModel):
    """A user-explicit request to score a fixed result snapshot."""

    intent_snapshot_id: int = Field(gt=0)
    algorithm_version: str = Field(default="ranking-v3.0", min_length=1, max_length=100)
    include_external_metrics: bool = False
    include_pico: bool = True
    force_refresh: bool = False


class ResearchIntentSnapshotCreate(BaseModel):
    """Explicit confirmation record; edits produce a new immutable snapshot."""

    research_context_id: int = Field(gt=0)
    dimensions: dict[str, str] = Field(default_factory=dict)
    confirmation_status: Literal["candidate", "user_confirmed"] = "candidate"


class ScoringRunRead(BaseModel):
    generation_id: int
    status: ScoringRunStatus
    algorithm_version: str
    operation: Literal["created", "reused"]


class ScoringStatusRead(BaseModel):
    active_generation_id: int | None = None
    building_generation_id: int | None = None
    status: ScoringRunStatus
    completed: int = 0
    total: int = 0
    started_at: datetime | None = None
    updated_at: datetime | None = None
    algorithm_version: str | None = None
    signals: dict[str, str] = Field(default_factory=dict)
    last_error: str | None = None
    can_retry: bool = False


class ScoreExplanationRead(BaseModel):
    """Evidence is persisted at generation time; this endpoint never calls providers."""

    result_id: int
    pmid: str
    generation_id: int
    algorithm_version: str
    eligibility: dict[str, object]
    components: dict[str, object]
    evidence: list[dict[str, object]]
    limitations: list[str]
