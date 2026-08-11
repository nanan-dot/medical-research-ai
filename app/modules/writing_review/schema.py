"""Contracts for simulated writing reviews."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.writing_review.roles import ReviewerRole


class CustomReviewer(BaseModel):
    identity: str = Field(min_length=3, max_length=100)
    expertise: str = Field(min_length=10, max_length=1000)
    limitations: str = Field(min_length=10, max_length=1000)


class WritingReviewRequest(BaseModel):
    expected_version: int = Field(gt=0)
    segment_ids: list[str] = Field(min_length=1, max_length=30)
    evidence_reference_ids: list[int] = Field(min_length=1, max_length=50)
    role: ReviewerRole | None = None
    custom_reviewer: CustomReviewer | None = None
    model_config_id: int = Field(gt=0)

    @model_validator(mode="after")
    def require_exactly_one_role(self) -> "WritingReviewRequest":
        if (self.role is None) == (self.custom_reviewer is None):
            raise ValueError("Provide exactly one preset role or custom reviewer")
        return self


class ReviewFinding(BaseModel):
    severity: str = Field(pattern="^(blocker|major|minor)$")
    segment_id: str = Field(min_length=1, max_length=200)
    issue: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(min_length=1, max_length=2000)
    evidence_status: str = Field(min_length=1, max_length=100)
    recommendation: str = Field(min_length=1, max_length=2000)


class WritingReviewRead(BaseModel):
    id: int
    project_id: int
    simulated: bool
    reviewer_label: str
    findings: list[ReviewFinding]
    created_at: datetime
