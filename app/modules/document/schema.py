"""Document API contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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


class DocumentPage(BaseModel):
    items: list[DocumentRead]
    total: int
    offset: int
    limit: int
