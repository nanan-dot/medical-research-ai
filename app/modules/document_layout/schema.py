from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SegmentationState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SegmentationRead(BaseModel):
    id: int
    anchor_revision_id: int
    state: SegmentationState
    task_id: int | None = None
    algorithm_version: str
    config_hash: str
    segmentation_fingerprint: str | None = None
    quality_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    finished_at: datetime | None = None


class SegmentationManifestRead(BaseModel):
    document_id: int
    segmentation: SegmentationRead | None


class FragmentRead(BaseModel):
    page_number: int
    start_item_index: int
    end_item_index: int


class SegmentRead(BaseModel):
    id: int
    segment_key: str
    reading_order: int
    segment_type: str
    text: str
    section_path: list[str]
    translation_eligibility: str
    quality_flags: list[str]
    first_page: int
    last_page: int
    fragments: list[FragmentRead]


class SegmentPageRead(BaseModel):
    anchor_revision_id: int | None = None
    segmentation_revision_id: int | None = None
    items: list[SegmentRead]
    offset: int
    limit: int
    total: int


class SectionRead(BaseModel):
    id: int
    literal_title: str
    canonical_role: str | None
    level: int
    first_page: int
    last_page: int
