"""Durable queue submission for document work; execution lives in the worker."""

import json
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus


class DocumentTaskService:
    """Create independently trackable document tasks without executing work in HTTP."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = TaskRepository(session)

    async def enqueue(self, document_id: int, operation: str) -> TaskRecord:
        """Return the active task for one document operation instead of duplicating work."""
        idempotency_key = f"document:{document_id}:{operation}"
        active = await self._repository.find_active_by_key(idempotency_key)
        if active is not None:
            return active
        task = TaskRecord(
            task_type="document_operation",
            title=f"Document {operation}",
            status=TaskStatus.QUEUED.value,
            progress=0,
            source_type="document",
            source_id=document_id,
            detail_json=json.dumps({"operation": operation, "stage": "queued", "actor_id": "local"}),
            idempotency_key=idempotency_key,
        )
        return await self._repository.create(task)

    async def enqueue_many(self, document_ids: list[int], operation: str) -> tuple[str, list[TaskRecord]]:
        operation_id = f"batch_{uuid4().hex}"
        tasks = [await self.enqueue(document_id, operation) for document_id in dict.fromkeys(document_ids)]
        return operation_id, tasks
