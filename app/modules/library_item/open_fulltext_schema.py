"""Boundary contracts for verified PMC open-full-text acquisition."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.library_item.schema import LibraryItemRead


class OpenFulltextStatus(StrEnum):
    SUCCEEDED = "succeeded"
    IDENTITY_MISMATCH = "identity_mismatch"
    LICENSE_UNVERIFIED = "license_unverified"
    PDF_UNAVAILABLE = "pdf_unavailable"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    CONTENT_INVALID = "content_invalid"
    STORAGE_FAILED = "storage_failed"


class OpenFulltextRequest(BaseModel):
    pmcid: str = Field(min_length=4, max_length=32)

    @field_validator("pmcid")
    @classmethod
    def normalize_pmcid(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.startswith("PMC") or not normalized[3:].isdigit():
            raise ValueError("PMCID must have the form PMC followed by digits")
        return normalized


class OpenFulltextAcquisitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    library_item_id: int
    document_id: int | None
    pmcid: str
    status: OpenFulltextStatus
    source_url: str | None
    license: str | None
    file_format: str | None
    file_sha256: str | None
    error_code: str | None
    error_message: str | None
    attempted_at: datetime
    retrieved_at: datetime | None


class OpenFulltextResult(BaseModel):
    item: LibraryItemRead
    acquisition: OpenFulltextAcquisitionRead
