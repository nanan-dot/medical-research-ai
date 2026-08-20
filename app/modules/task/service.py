"""统一任务中心的业务编排。"""

import json

from app.common.exceptions import NotFoundError
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskCreate, TaskPage, TaskRead, TaskStatus


class TaskService:
    """提供通用任务记录的创建、查询和分页展示能力。"""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(self, payload: TaskCreate) -> TaskRead:
        """创建待执行任务记录，不在 API 请求内伪造执行完成。"""
        task = await self._repository.create(
            TaskRecord(
                task_type=payload.task_type,
                title=payload.title,
                status=TaskStatus.PENDING.value,
                progress=0,
                source_type=payload.source_type,
                source_id=payload.source_id,
                detail_json=json.dumps(payload.detail, ensure_ascii=False),
            )
        )
        return self._to_read(task)

    async def get(self, task_id: int) -> TaskRead:
        """读取任务，任务不存在时返回统一的 404 领域错误。"""
        task = await self._repository.get(task_id)
        if task is None:
            raise NotFoundError(f"Task not found: {task_id}")
        return self._to_read(task)

    async def list(
        self, offset: int, limit: int, status: TaskStatus | None
    ) -> TaskPage:
        """返回任务记录与匹配总数。"""
        tasks = await self._repository.list(offset, limit, status)
        total = await self._repository.count(status)
        return TaskPage(
            items=[self._to_read(task) for task in tasks],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def cancel(self, task_id: int) -> TaskRead:
        task = await self._required(task_id)
        if task.status not in {TaskStatus.PENDING.value, TaskStatus.QUEUED.value, TaskStatus.RUNNING.value}:
            raise ValueError("Only pending, queued, or running tasks can be cancelled")
        task.status = TaskStatus.CANCELLED.value
        await self._repository.session.flush()
        return self._to_read(task)

    async def retry(self, task_id: int) -> TaskRead:
        task = await self._required(task_id)
        if task.status != TaskStatus.FAILED.value:
            raise ValueError("Only failed tasks can be retried")
        task.status = TaskStatus.QUEUED.value
        task.progress = 0
        task.error_code = None
        task.error_message = None
        task.finished_at = None
        await self._repository.session.flush()
        return self._to_read(task)

    async def _required(self, task_id: int) -> TaskRecord:
        task = await self._repository.get(task_id)
        if task is None:
            raise NotFoundError(f"Task not found: {task_id}")
        return task

    @staticmethod
    def _to_read(task: TaskRecord) -> TaskRead:
        """将持久化 JSON 详情转换为受限 API 数据。"""
        detail = json.loads(task.detail_json)
        if not isinstance(detail, dict):
            detail = {}
        return TaskRead(
            id=task.id,
            task_type=task.task_type,
            title=task.title,
            status=TaskStatus(task.status),
            progress=task.progress,
            source_type=task.source_type,
            source_id=task.source_id,
            detail=detail,
            error_code=task.error_code,
            error_message=task.error_message,
            retry_count=task.retry_count,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            resource_type=task.source_type,
            resource_id=task.source_id,
            operation=detail.get("operation") if isinstance(detail.get("operation"), str) else None,
            stage=detail.get("stage") if isinstance(detail.get("stage"), str) else None,
        )
