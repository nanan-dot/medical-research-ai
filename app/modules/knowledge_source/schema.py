"""Knowledge-source API contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.knowledge_source.auto_sync_policy import (
    MAX_SYNC_INTERVAL_MINUTES,
    MIN_SYNC_INTERVAL_MINUTES,
)


class KnowledgeSourceType(StrEnum):
    LOCAL_FOLDER = "local_folder"
    OBSIDIAN_VAULT = "obsidian_vault"
    TEMPORARY_IMPORT = "temporary_import"
    ZOTERO_LIBRARY = "zotero_library"


class KnowledgeSourceSyncStatus(StrEnum):
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    UNAVAILABLE = "unavailable"


class KnowledgeSourceHealthStatus(StrEnum):
    READY = "ready"
    SYNCING = "syncing"
    NEEDS_ATTENTION = "needs_attention"
    PAUSED = "paused"
    UNAVAILABLE = "unavailable"


class KnowledgeSourceSortBy(StrEnum):
    PINNED = "pinned"
    LAST_SYNC = "last_sync"
    LAST_OPENED = "last_opened"
    NAME = "name"
    DOCUMENT_COUNT = "document_count"


class KnowledgeSourceCreate(BaseModel):
    """创建请求"""

    name: str = Field(min_length=1, max_length=200)
    source_type: KnowledgeSourceType
    root_path: str = Field(min_length=1)
    enabled: bool = True

    @field_validator("name", "root_path")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class KnowledgeSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    auto_sync: bool | None = None
    sync_interval_minutes: int | None = Field(
        default=None,
        ge=MIN_SYNC_INTERVAL_MINUTES,
        le=MAX_SYNC_INTERVAL_MINUTES,
    )
    is_pinned: bool | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class KnowledgeSourceStats(BaseModel):
    """一个知识源的实时文档处理统计。"""

    total_files: int = 0
    parsed: int = 0
    indexed: int = 0
    pending: int = 0
    failed: int = 0
    available: int = 0
    processing: int = 0
    needs_attention: int = 0
    availability_percent: float | None = None


class KnowledgeSourceResearchContextRead(BaseModel):
    """来源列表中的精简研究项目摘要。"""

    id: int
    name: str


class KnowledgeSourceRead(BaseModel):
    """查询响应"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: KnowledgeSourceType
    root_path: str
    enabled: bool
    auto_sync: bool
    sync_interval_minutes: int = 60
    next_auto_sync_at: datetime | None = None
    is_pinned: bool
    sync_status: KnowledgeSourceSyncStatus
    last_sync_time: datetime | None
    last_opened_at: datetime | None = None
    last_opened_by: str | None = None
    research_contexts: list[KnowledgeSourceResearchContextRead] = Field(
        default_factory=list
    )
    research_context_count: int = 0
    error_message: str | None
    health_status: KnowledgeSourceHealthStatus = KnowledgeSourceHealthStatus.READY
    stats: KnowledgeSourceStats = Field(default_factory=KnowledgeSourceStats)


class KnowledgeSourcePage(BaseModel):
    """A filtered knowledge-source page with total independent of its slice."""

    items: list[KnowledgeSourceRead]
    total: int
    offset: int
    limit: int


class KnowledgeBaseIssueBreakdown(BaseModel):
    parse_failed: int = 0
    unsupported_format: int = 0
    unavailable_file: int = 0
    index_failed: int = 0
    other: int = 0


class KnowledgeBaseSummary(BaseModel):
    source_count: int = 0
    local_folder_count: int = 0
    obsidian_count: int = 0
    total_item_count: int = 0
    available_item_count: int = 0
    processing_item_count: int = 0
    needs_attention_count: int = 0
    affected_source_count: int = 0
    availability_percent: float | None = None
    issue_breakdown: KnowledgeBaseIssueBreakdown = Field(
        default_factory=KnowledgeBaseIssueBreakdown
    )


class KnowledgeSourceSyncSummary(BaseModel):
    knowledge_source_id: int
    sync_status: KnowledgeSourceSyncStatus
    last_sync_time: datetime | None
    added: int
    modified: int
    deleted: int
    skipped: int
    failed: int
    error_message: str | None


class KnowledgeSourceSyncAccepted(BaseModel):
    """Durable sync submission result; execution occurs in an explicit worker."""

    task_id: int
    knowledge_source_id: int
    status: str
    status_url: str


class KnowledgeSourceDirectoryBrowseRead(BaseModel):
    """授权目录选择器的结果；取消选择时路径为空。"""

    path: str | None


class KnowledgeSourceDocumentImportRead(BaseModel):
    """单篇导入完成后返回文档与归属知识库。"""

    document_id: int
    knowledge_source_id: int
    original_filename: str
    stored_relative_path: str
