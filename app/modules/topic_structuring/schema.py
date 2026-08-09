"""API and snapshot structures for topic structuring."""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.literature_search.query_model import SearchIntentCandidate
from app.modules.topic_structuring.structure_classifier import StructuringStatus

ClarifiesField = Literal[
    "disease",
    "target",
    "intervention",
    "mechanism",
    "comparator",
    "outcome",
    "study_type",
    "general",
]
EditableField = Literal[
    "disease",
    "target",
    "intervention",
    "mechanism",
    "comparator",
    "outcome",
    "study_type",
    "focus_points",
]


class ClarificationQuestion(BaseModel):
    """Question whose answer can safely update one structured field."""

    id: UUID = Field(default_factory=uuid4)
    question: str = Field(min_length=1, max_length=500)
    clarifies_field: ClarifiesField = "general"
    answered: bool = False


class TopicStructureCandidate(BaseModel):
    """A candidate that reuses R2 search-intent names for shared concepts."""

    structuring_status: StructuringStatus
    reason: str | None = Field(default=None, max_length=1000)
    # Reuse R2-WP02 names rather than creating parallel PICO disease/intervention schemas.
    disease: str | None = Field(default=None, max_length=200)
    intervention: str | None = Field(default=None, max_length=200)
    target: str | None = Field(default=None, max_length=200)
    mechanism: str | None = Field(default=None, max_length=200)
    comparator: str | None = Field(default=None, max_length=200)
    outcome: str | None = Field(default=None, max_length=200)
    study_type: str | None = Field(default=None, max_length=100)
    focus_points: list[str] = Field(default_factory=list, max_length=10)
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list, max_length=10
    )
    known_fields: dict[EditableField, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unstructured_content(self) -> "TopicStructureCandidate":
        if self.structuring_status == "unstructured" and not self.reason:
            raise ValueError("unstructured candidate requires a reason")
        return self

    def to_search_intent(self, topic: str) -> SearchIntentCandidate:
        """Expose the exact R2 shared field mapping for downstream search integration."""
        return SearchIntentCandidate(
            topic=topic,
            disease=self.disease,
            intervention=self.intervention,
            target=self.target,
            mechanism=self.mechanism,
            study_types=[] if self.study_type is None else [self.study_type],
        )


class TopicStructuringParseRequest(BaseModel):
    topic: str = Field(min_length=8, max_length=1000)
    model_config_id: int | None = Field(default=None, ge=1)


class TopicStructuringPatchRequest(BaseModel):
    field: EditableField | None = None
    value: str | list[str] | None = None
    clarification_question_id: UUID | None = None
    answer: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_patch_mode(self) -> "TopicStructuringPatchRequest":
        has_field_update = self.field is not None
        has_answer = (
            self.clarification_question_id is not None or self.answer is not None
        )
        if has_field_update == has_answer:
            raise ValueError(
                "send either field/value or clarification_question_id/answer"
            )
        if has_field_update and self.value is None:
            raise ValueError("field updates require value")
        if has_answer and (
            self.clarification_question_id is None or self.answer is None
        ):
            raise ValueError("clarification updates require question id and answer")
        return self


class TopicStructuringVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    created_at: datetime
    candidate: TopicStructureCandidate


class TopicStructuringRead(BaseModel):
    id: int
    original_topic: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    candidate: TopicStructureCandidate
    versions: list[TopicStructuringVersionRead] = Field(default_factory=list)
