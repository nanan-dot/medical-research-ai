"""HTTP contracts for A0 revision creation and inspection."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AnchorRevisionState(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    READY = "ready"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"
    STALE = "stale"
    CANCELLED = "cancelled"


class AnchorRevisionRequest(BaseModel):
    expected_file_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    force_new_toolchain_run: bool = False


class AnchorRevisionRead(BaseModel):
    id: int
    document_id: int
    file_hash: str
    state: AnchorRevisionState
    task_id: int | None = None
    pdfjs_version: str
    normalization_version: str
    extraction_fingerprint: str | None = None
    request_fingerprint: str
    extractor_version: str
    options_hash: str
    quality_summary: dict[str, object]
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class AnchorManifestRead(BaseModel):
    document_id: int
    revision: AnchorRevisionRead | None


class SourcePageQualityRead(BaseModel):
    revision_id: int
    document_id: int
    page_number: int
    text_item_count: int
    quality_flags: list[str]
    quality_metrics: dict[str, object] = Field(default_factory=dict)
