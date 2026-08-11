"""Public contracts for evidence-bound writing suggestions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

WritingTask = Literal["outline", "draft", "rewrite"]


class EvidenceInput(BaseModel):
    reference_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=12000)


class WritingGenerationRequest(BaseModel):
    expected_version: int = Field(gt=0)
    task: WritingTask
    evidence: list[EvidenceInput] = Field(min_length=1, max_length=50)
    selected_segment_id: str | None = Field(default=None, min_length=1, max_length=200)
    model_config_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_evidence_for_generation(self) -> "WritingGenerationRequest":
        if not self.evidence:
            raise ValueError("At least one authorized evidence item is required")
        return self


class EvidenceMapping(BaseModel):
    evidence_ref: int = Field(gt=0)
    citation_id: str = Field(min_length=1, max_length=300)


class SuggestedSegment(BaseModel):
    text: str = Field(min_length=1)
    evidence_reference_ids: list[int] = Field(default_factory=list)
    needs_verification: bool = False


class StructuredSuggestion(BaseModel):
    content: str = Field(min_length=1)
    segments: list[SuggestedSegment] = Field(min_length=1)


class WritingSuggestionRead(BaseModel):
    id: int
    project_id: int
    task: WritingTask
    content: str
    evidence_mappings: list[EvidenceMapping]
    requires_human_confirmation: bool
    confirmed_at: datetime | None
    adopted_version: int | None
    created_at: datetime
