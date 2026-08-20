"""统一任务中心的 API 契约。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(StrEnum):
    """任务中心的可见状态。"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class TaskCreate(BaseModel):
    """创建任务记录；实际执行器由对应业务模块负责。"""

    task_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    source_type: str | None = Field(default=None, max_length=64)
    source_id: int | None = Field(default=None, ge=1)
    detail: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TaskRead(BaseModel):
    """任务中心返回的可展示任务状态。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: str
    title: str
    status: TaskStatus
    progress: int
    source_type: str | None
    source_id: int | None
    detail: dict[str, str | int | float | bool | None]
    error_code: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    resource_type: str | None = None
    resource_id: int | None = None
    operation: str | None = None
    stage: str | None = None


class TaskPage(BaseModel):
    """分页任务列表。"""

    items: list[TaskRead]
    total: int
    offset: int
    limit: int
