"""API contracts for explainable feasibility scoring."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DimensionName = Literal[
    "literature_base",
    "novelty_uncertainty",
    "technical_feasibility",
    "sample_availability",
    "data_availability",
    "timeline",
    "budget",
    "ethics",
    "analysis_difficulty",
    "advisor_alignment",
]
ScoreSource = Literal["system", "user", "unknown"]
Confidence = Literal["high", "medium", "low"]
USER_DIMENSIONS = frozenset(
    {
        "sample_availability",
        "data_availability",
        "timeline",
        "budget",
        "ethics",
    }
)


class UserAssessment(BaseModel):
    """A user-provided assessment for an operational feasibility dimension."""

    dimension: DimensionName
    score: float | None = Field(default=None, ge=0, le=100)
    basis: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_user_dimension(self) -> "UserAssessment":
        if self.dimension not in USER_DIMENSIONS:
            raise ValueError("Only user dimensions accept user assessments")
        if self.score is not None and not self.basis:
            raise ValueError("A user score requires an explanation")
        return self


class FeasibilityRequest(BaseModel):
    """Create an initial score with optional per-request weight overrides."""

    weights: dict[DimensionName, float] | None = None
    user_assessments: list[UserAssessment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_assessments(self) -> "FeasibilityRequest":
        if len({item.dimension for item in self.user_assessments}) != len(
            self.user_assessments
        ):
            raise ValueError("User assessments must be unique")
        return self


class WeightPatch(BaseModel):
    """Change selected weights while inheriting the previous user assessments."""

    weights: dict[DimensionName, float]


class DimensionScore(BaseModel):
    dimension: DimensionName
    score: float | None
    weight: float
    basis: str
    score_source: ScoreSource


class FeasibilityRead(BaseModel):
    id: int
    direction_id: int
    version: int
    dimensions: list[DimensionScore]
    weights: dict[DimensionName, float]
    total_score: float
    confidence: Confidence
    missing_inputs: list[DimensionName]
    ranking_sensitive: bool
    created_at: datetime
