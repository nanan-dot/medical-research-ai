"""Knowledge-source API contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeSourceType(StrEnum):
    LOCAL_FOLDER = "local_folder"
    OBSIDIAN_VAULT = "obsidian_vault"
    TEMPORARY_IMPORT = "temporary_import"


class KnowledgeSourceSyncStatus(StrEnum):
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    UNAVAILABLE = "unavailable"


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


class KnowledgeSourceRead(BaseModel):
    """查询响应"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: KnowledgeSourceType
    root_path: str
    enabled: bool
    sync_status: KnowledgeSourceSyncStatus
    last_sync_time: datetime | None
    error_message: str | None
    stats: KnowledgeSourceStats = Field(default_factory=KnowledgeSourceStats)


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
