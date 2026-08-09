from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FeedbackErrorType(StrEnum):
    BLOCKER = "blocker"
    SEVERE = "severe"
    GENERAL = "general"
    NONE = "none"


class FeedbackCreate(BaseModel):
    task_completion_rate: float = Field(ge=0, le=1)
    useful: bool | None = None
    citation_correct: bool | None = None
    data_correct: bool | None = None
    error_type: FeedbackErrorType | None = None
    comment: str | None = Field(default=None, max_length=2000)
    next_step: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_observation(self):
        if all(
            value is None
            for value in (
                self.useful,
                self.citation_correct,
                self.data_correct,
                self.error_type,
                self.comment,
                self.next_step,
            )
        ):
            raise ValueError("At least one structured answer or comment is required")
        return self


class FeedbackRead(BaseModel):
    id: int
    task_completion_rate: float
    useful: bool | None
    citation_correct: bool | None
    data_correct: bool | None
    error_type: FeedbackErrorType | None
    comment: str | None
    next_step: str | None
    created_at: datetime
