"""Document API contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MAX_DOCUMENT_QUERY_LENGTH = 200


class DocumentScanState(StrEnum):
    PENDING = "pending"
    OUTDATED = "outdated"


class ParseStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    OUTDATED = "outdated"


class DocumentMode(StrEnum):
    DOCUMENT = "document"
    CONTENT = "content"


class DocumentFileType(StrEnum):
    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"
    MARKDOWN = "markdown"
    TXT = "txt"
    OTHER = "other"


class DocumentHealthStatus(StrEnum):
    AVAILABLE = "available"
    PROCESSING = "processing"
    NEEDS_ATTENTION = "needs_attention"


class DocumentSortBy(StrEnum):
    UPDATED_AT = "updated_at"
    NAME = "name"
    FILE_SIZE = "file_size"


class ContentLocatorType(StrEnum):
    PAGE = "page"
    SLIDE = "slide"
    SECTION = "section"
    UNKNOWN = "unknown"


class DocumentCreate(BaseModel):
    """创建请求"""

    knowledge_source_id: int
    file_path: str
    normalized_file_path: str
    file_hash: str
    file_size: int
    modified_time: datetime
    modified_time_ns: int
    scan_state: DocumentScanState = DocumentScanState.PENDING


class DocumentRead(BaseModel):
    """查询响应"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    knowledge_source_id: int
    file_path: str
    original_filename: str | None = None
    media_type: str | None = None
    file_hash: str
    file_size: int
    modified_time: datetime
    scan_state: DocumentScanState
    parse_status: ParseStatus
    index_status: IndexStatus
    error_code: str | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    finished_at: datetime | None
    paperqa_index_key: str | None
    paperqa_version: str | None
    indexed_hash: str | None
    index_error: str | None
    parsed_is_scanned: bool | None
    file_type: DocumentFileType = DocumentFileType.OTHER
    extension: str | None = None
    preview_capability: bool = False
    health_status: DocumentHealthStatus = DocumentHealthStatus.PROCESSING
    health_reason: str | None = None
    available_actions: list[str] = Field(default_factory=list)
    progress: int | None = None
    task_id: int | None = None


class DocumentStatistics(BaseModel):
    total: int
    available: int
    processing: int
    needs_attention: int


class DocumentRepairRead(BaseModel):
    document_id: int
    action: str
    task_id: int | None = None
    status: str
    health_status: DocumentHealthStatus


class DocumentBatchTaskRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=100)


class DocumentBatchTaskItem(BaseModel):
    document_id: int
    task_id: int | None
    accepted: bool
    error_code: str | None = None


class DocumentBatchTaskRead(BaseModel):
    operation_id: str
    accepted: int
    items: list[DocumentBatchTaskItem]


class DocumentPage(BaseModel):
    items: list[DocumentRead]
    total: int
    offset: int
    limit: int


class ContentSearchResult(BaseModel):
    """A real parsed-content match and the strongest available source locator."""

    document_id: int
    document_name: str
    knowledge_source_id: int
    source_name: str
    locator_type: ContentLocatorType
    locator: str | None = None
    snippet: str
    score: float | None = None


class ContentSearchPage(BaseModel):
    """A server-paginated content-search response."""

    items: list[ContentSearchResult]
    total: int
    offset: int
    limit: int


class DocumentIndexResult(BaseModel):
    document_id: int
    index_status: IndexStatus
    paperqa_index_key: str | None
    paperqa_version: str | None
    indexed_hash: str | None
    reused: bool
    error_code: str | None = None
    error_message: str | None = None


class BatchIndexRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=100)


class BatchIndexResult(BaseModel):
    results: list[DocumentIndexResult]
    succeeded: int
    failed: int
