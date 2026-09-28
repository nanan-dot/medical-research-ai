"""Bounded public API contracts for Phase 1 translation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.document_selection.schema import AnchorReference, SelectionVersion
from app.modules.medical_translation.constants import (
    MAX_TRANSLATION_CHARACTERS,
    PHASE2_MAX_SEGMENTS_PER_INTENT,
)


class TranslationJobCreate(AnchorReference):
    source_language: str = Field(
        default="en", min_length=2, max_length=16, pattern=r"^[A-Za-z-]+$"
    )
    target_language: str = Field(
        default="zh-CN", min_length=2, max_length=16, pattern=r"^[A-Za-z-]+$"
    )

    @model_validator(mode="after")
    def languages_differ(self) -> "TranslationJobCreate":
        if self.source_language.lower() == self.target_language.lower():
            raise ValueError("source and target languages must differ")
        return self


class TranslationJobRead(BaseModel):
    id: int
    task_id: int
    document_id: int
    source_anchor_id: int
    layout_segment_id: int | None = None
    state: Literal[
        "queued", "running", "quality_checking", "succeeded", "failed", "cancelled"
    ]
    source_language: str
    target_language: str
    attempt_count: int
    result_revision_id: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None


class QualityIssueRead(BaseModel):
    code: str
    severity: str
    blocking: bool
    message: str
    source_span: tuple[int, int] | None = None
    target_span: tuple[int, int] | None = None


class TermEvidenceRead(BaseModel):
    source_term: str
    target_term: str | None
    status: str
    provenance: str
    version: str
    authority: str | None = None
    source_span: tuple[int, int] | None = None


class TranslationRevisionRead(BaseModel):
    id: int
    document_id: int
    source_anchor_id: int
    version: int
    origin: str
    source_language: str
    target_language: str
    translated_text: str
    alignment: list[dict[str, object]]
    terms: list[TermEvidenceRead]
    issues: list[QualityIssueRead]
    quality_status: Literal[
        "machine_checked", "needs_review", "blocked", "human_reviewed"
    ]
    provider: str
    model: str
    created_at: datetime


class TranslationCorrectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    translated_text: str = Field(min_length=1, max_length=MAX_TRANSLATION_CHARACTERS)
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def nonblank(self) -> "TranslationCorrectionCreate":
        if not self.translated_text.strip():
            raise ValueError("translated_text must not be blank")
        return self


class TranslationRevisionPage(BaseModel):
    items: list[TranslationRevisionRead]
    total: int
    offset: int
    limit: int


class TranslationTermOverrideCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_term: str = Field(min_length=1, max_length=256)
    target_term: str = Field(min_length=1, max_length=256)
    target_language: str = Field(default="zh-CN", min_length=2, max_length=16)

    @model_validator(mode="after")
    def nonblank(self) -> "TranslationTermOverrideCreate":
        if not self.source_term.strip() or not self.target_term.strip():
            raise ValueError("term values must not be blank")
        return self


class TranslationTermOverrideRead(BaseModel):
    id: int
    document_id: int
    source_term: str
    target_term: str
    target_language: str
    scope: Literal["document"]
    created_at: datetime
    updated_at: datetime


class TranslationSegmentIntentCreate(SelectionVersion):
    """A bounded, version-pinned request to prepare translations for A1 segments."""

    segment_ids: list[int] = Field(min_length=1, max_length=PHASE2_MAX_SEGMENTS_PER_INTENT)
    active_segment_id: int | None = Field(default=None, gt=0)
    trigger: Literal["follow", "visible", "prefetch"] = "follow"
    source_language: str = Field(default="en", min_length=2, max_length=16)
    target_language: str = Field(default="zh-CN", min_length=2, max_length=16)

    @model_validator(mode="after")
    def active_segment_is_requested(self) -> "TranslationSegmentIntentCreate":
        if self.active_segment_id is not None and self.active_segment_id not in self.segment_ids:
            raise ValueError("active_segment_id must be included in segment_ids")
        return self


class TranslationSegmentStatusRead(BaseModel):
    segment_id: int
    translation_eligibility: str
    state: Literal["cached", "queued", "running", "cooling_down", "degraded"]
    job: TranslationJobRead | None = None
    revision: TranslationRevisionRead | None = None
    degraded_reason: str | None = None


class TranslationPrefetchIntentRead(BaseModel):
    generation: str
    items: list[TranslationSegmentStatusRead]
    queued_count: int
    deduplicated_count: int
