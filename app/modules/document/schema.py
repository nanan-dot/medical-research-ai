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


class DocumentPage(BaseModel):
    items: list[DocumentRead]
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
