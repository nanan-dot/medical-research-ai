"""Durable worker that executes queued document operations outside HTTP requests."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.index_service import DocumentIndexService
from app.modules.document.service import DocumentService, sanitize_error_message
from app.modules.task.model import TaskRecord
from app.modules.task.schema import TaskStatus


class DocumentTaskWorker:
    """Consume one durable document task at a time using independent DB sessions."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run_once(self) -> bool:
        async with self._session_factory() as session:
            task = await session.scalar(
                select(TaskRecord)
                .where(TaskRecord.task_type == "document_operation", TaskRecord.status == TaskStatus.QUEUED.value)
                .order_by(TaskRecord.created_at, TaskRecord.id)
                .limit(1)
            )
            if task is None:
                return False
            task.status = TaskStatus.RUNNING.value
            task.progress = 1
            task.started_at = task.started_at or task.created_at
            await session.commit()
            task_id = task.id

        async with self._session_factory() as session:
            task = await session.get(TaskRecord, task_id)
            if task is None or task.status == TaskStatus.CANCELLED.value:
                return True
            try:
                detail = json.loads(task.detail_json)
                operation = detail.get("operation")
                if not isinstance(operation, str) or task.source_id is None:
                    raise ValueError("Document task payload is invalid")
                service = DocumentService(session)
                if operation in {"repair", "reparse"}:
                    detail["stage"] = "parsing"
                    task.progress = 5
                    await session.flush()
                    if operation == "repair":
                        document, action = await service.repair(task.source_id)
                        if action == "retry_index":
                            detail["stage"] = "indexing"
                            task.progress = 70
                            await DocumentIndexService(session).index(document.id)
                    else:
                        document = await service.get(task.source_id)
                        await service.retry_parse(document.id)
                elif operation == "reindex":
                    detail["stage"] = "indexing"
                    task.progress = 70
                    document = await service.get(task.source_id)
                    await service.retry_index(document.id)
                    await DocumentIndexService(session).index(document.id)
                else:
                    raise ValueError("Document task operation is unsupported")
                detail["stage"] = "completed"
                task.detail_json = json.dumps(detail, ensure_ascii=False)
                task.status = TaskStatus.SUCCEEDED.value
                task.progress = 100
                task.finished_at = datetime.now(UTC)
                await session.commit()
            except Exception as exc:  # noqa: BLE001 -- worker must persist a safe terminal failure.
                task.status = TaskStatus.FAILED.value
                task.error_code = getattr(exc, "code", "document_task_failed")
                task.error_message = sanitize_error_message(str(exc))
                task.progress = 100
                task.finished_at = datetime.now(UTC)
                await session.commit()
            return True
