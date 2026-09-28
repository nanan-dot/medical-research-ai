"""API contracts for formal local-library records."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FulltextStatus(StrEnum):
    METADATA_ONLY = "metadata_only"
    LOCAL_PDF_AVAILABLE = "local_pdf_available"
    OPEN_ACCESS_AVAILABLE = "open_access_available"
    UNAVAILABLE = "unavailable"


class LinkLocalPdfRequest(BaseModel):
    document_id: int | None = Field(default=None, ge=1)


class SaveLibraryItemRequest(BaseModel):
    pmid: str = Field(min_length=1, max_length=20)


class LibraryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pmid: str | None
    pmcid: str | None
    doi: str | None
    title: str | None
    journal: str | None
    year: int | None
    document_id: int | None
    source_search_id: int | None
    fulltext_status: FulltextStatus
    fulltext_status_reason: str
    created_at: datetime
    updated_at: datetime


class LibraryItemPage(BaseModel):
    items: list[LibraryItemRead]
    total: int
    offset: int
    limit: int
