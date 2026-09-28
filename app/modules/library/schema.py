"""Pydantic contracts for the unified research-resource library."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.modules.document.schema import DocumentRead

MAX_LIBRARY_QUERY_LENGTH = 200


class LibrarySourceType(StrEnum):
    LOCAL_FOLDER = "local_folder"
    OBSIDIAN_VAULT = "obsidian_vault"
    ZOTERO_LIBRARY = "zotero_library"
    TEMPORARY_IMPORT = "temporary_import"


class LibraryHealthStatus(StrEnum):
    AI_AVAILABLE = "ai_available"
    PROCESSING = "processing"
    NEEDS_PROCESSING = "needs_processing"
    OUTDATED = "outdated"
    NEEDS_ATTENTION = "needs_attention"
    METADATA_ONLY = "metadata_only"


class LibrarySortBy(StrEnum):
    UPDATED_AT = "updated_at"
    NAME = "name"
    FILE_SIZE = "file_size"
    SOURCE_NAME = "source_name"
    STATUS = "status"
    LAST_OPENED = "last_opened"


class LibraryIssueBreakdown(BaseModel):
    parse_failed: int = 0
    unsupported_format: int = 0
    unavailable_file: int = 0
    index_failed: int = 0
    other: int = 0


class LibrarySourceTypeCount(BaseModel):
    source_type: LibrarySourceType
    count: int


class LibrarySummary(BaseModel):
    """Global fact-derived document and processing statistics."""

    total: int = 0
    processed: int = 0
    ai_available: int = 0
    processing: int = 0
    needs_attention: int = 0
    issue_breakdown: LibraryIssueBreakdown = Field(default_factory=LibraryIssueBreakdown)
    source_types: list[LibrarySourceTypeCount] = Field(default_factory=list)
    snapshot_at: datetime


class LibraryFacetValue(BaseModel):
    value: str
    count: int


class LibraryFacets(BaseModel):
    """Facets use all filters except their own dimension (self-excluding semantics)."""

    sources: list[LibraryFacetValue] = Field(default_factory=list)
    source_types: list[LibraryFacetValue] = Field(default_factory=list)
    file_types: list[LibraryFacetValue] = Field(default_factory=list)
    statuses: list[LibraryFacetValue] = Field(default_factory=list)


class LibraryItemRead(DocumentRead):
    """A document list/detail record with safe library-facing metadata."""

    source_name: str
    source_type: LibrarySourceType
    relative_path: str
    display_name: str
    task_status: str | None = None
    phase: str | None = None
    current_item: str | None = None
    last_opened_at: datetime | None = None
    open_count: int = 0
    status: LibraryHealthStatus
    match_fields: list[str] = Field(default_factory=list)
    snippet: str | None = None
    locator: str | None = None


class LibraryItemPage(BaseModel):
    items: list[LibraryItemRead]
    total: int
    offset: int
    limit: int


class LibrarySourceTreeNode(BaseModel):
    node_id: str
    parent_id: str | None = None
    name: str
    relative_path: str = ""
    source_id: int | None = None
    direct_count: int = 0
    descendant_count: int = 0
    health: str
    children: list[LibrarySourceTreeNode] = Field(default_factory=list)


class LibrarySourceTreeGroup(BaseModel):
    source_type: str
    node_id: str
    descendant_count: int = 0
    health: str = "ready"
    children: list[LibrarySourceTreeNode] = Field(default_factory=list)


class LibrarySourceTree(BaseModel):
    groups: list[LibrarySourceTreeGroup]


class DocumentOpenedRequest(BaseModel):
    actor_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class DocumentOpenedRead(BaseModel):
    document_id: int
    last_opened_at: datetime
    last_opened_by: str | None = None
    open_count: int


class LibraryImportItem(BaseModel):
    original_filename: str
    status: str
    document_id: int | None = None
    task_id: int | None = None
    error_code: str | None = None
    message: str | None = None


class LibraryImportRead(BaseModel):
    items: list[LibraryImportItem]


class LibraryStorageSummary(BaseModel):
    managed_bytes: int
    external_source_bytes: int
    total_known_bytes: int
    quota_bytes: int | None = None
    usage_percent: float | None = None
    status: str
    measured_at: datetime


class ZoteroSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    library_type: str = Field(pattern="^(users|groups)$")
    library_id: str = Field(min_length=1, max_length=64)

    @field_validator("name", "library_id")
    @classmethod
    def strip_values(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("value must not be blank")
        return result


class ZoteroConnectionRead(BaseModel):
    status: str
    library_type: str
    library_id: str
    version: str | None = None
