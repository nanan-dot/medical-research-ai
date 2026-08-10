"""OCR 任务 API 契约。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class OcrJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OcrPageRead(BaseModel):
    page_number: int
    text: str | None
    confidence: float | None
    error_code: str | None
    error_message: str | None


class OcrJobRead(BaseModel):
    id: int
    document_id: int
    status: OcrJobStatus
    engine_name: str | None
    engine_version: str | None
    language: str
    page_count: int | None
    completed_pages: int
    failed_pages: int
    output_sha256: str | None
    error_code: str | None
    error_message: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    pages: list[OcrPageRead]
