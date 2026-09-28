"""论文阅读工作区稳定 API DTO。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.document_reader.constants import (
    EXPOSURE_MAX_BATCH_SIZE,
    EXPOSURE_MAX_EVENT_SPAN_SECONDS,
    EXPOSURE_MAX_MILLISECONDS,
)


class CapabilityState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RESERVED = "reserved"
    NOT_READY = "not_ready"


class ReaderPositionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(ge=1)
    viewport_offset_ratio: float = Field(ge=0, le=1)
    source_anchor_id: int | None = Field(default=None, gt=0)
    expected_version: int = Field(ge=1)
    expected_file_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ExposureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int = Field(ge=1)
    visible_milliseconds: int = Field(ge=0, le=EXPOSURE_MAX_MILLISECONDS)
    max_visible_ratio: float = Field(ge=0, le=1)
    first_visible_at: datetime
    last_visible_at: datetime

    @model_validator(mode="after")
    def validate_interval(self) -> "ExposureCreate":
        if self.last_visible_at < self.first_visible_at:
            raise ValueError("last_visible_at must not precede first_visible_at")
        if (self.last_visible_at - self.first_visible_at).total_seconds() > EXPOSURE_MAX_EVENT_SPAN_SECONDS:
            raise ValueError("exposure event span is too large")
        interval_milliseconds = int(
            (self.last_visible_at - self.first_visible_at).total_seconds() * 1000
        )
        if self.visible_milliseconds > interval_milliseconds:
            raise ValueError("visible_milliseconds exceeds observed interval")
        return self


class ExposureBatchCreate(BaseModel):
    exposures: list[ExposureCreate] = Field(min_length=1, max_length=EXPOSURE_MAX_BATCH_SIZE)
    expected_file_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=128)
    idempotency_payload_id: str | None = Field(default=None, max_length=128)


class SessionRead(BaseModel):
    id: int
    paper_item_id: int
    document_id: int
    file_hash: str
    page: int
    viewport_offset_ratio: float
    status: str
    version: int


class ProgressRead(BaseModel):
    qualified_pages: int
    total_pages: int
    percent: int


class CitationAnchorContext(BaseModel):
    source_anchor_id: int
    anchor_status: str


class ReaderCapabilities(BaseModel):
    outline: CapabilityState
    chapter_bundle: CapabilityState
    copilot: CapabilityState
    translation: CapabilityState


class TranslationCapabilityRead(BaseModel):
    state: CapabilityState
    contract_version: str
    endpoint: str | None = None


class PreferenceUpdate(BaseModel):
    view_mode: str | None = Field(default=None, pattern="^(original|bilingual|translated)$")
    zoom_percent: int | None = Field(default=None, ge=25, le=400)
    left_panel_mode: str | None = Field(default=None, max_length=32)
    left_collapsed: bool | None = None
    right_panel_tab: str | None = Field(default=None, max_length=32)
    focus_mode: bool | None = None
    expected_version: int = Field(ge=1)


class BookmarkCreate(BaseModel):
    source_anchor_id: int = Field(gt=0)
    label: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=32)


class QuestionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class QuestionCreate(BaseModel):
    source_anchor_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=4000)


class ResearchMaterialCreate(BaseModel):
    research_context_id: int = Field(gt=0)
    source_anchor_id: int = Field(gt=0)
    candidate_type: str = Field(pattern="^(quote|note|question)$")
    title: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=4000)


class HistoryCursor(BaseModel):
    last_seen_at: datetime
    session_id: int = Field(gt=0)
