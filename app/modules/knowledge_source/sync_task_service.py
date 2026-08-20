"""Durable manual knowledge-source sync submission and worker execution."""

import asyncio
import json
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.knowledge_source.schema import KnowledgeSourceSyncSummary
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus

logger = logging.getLogger(__name__)
TASK_TYPE = "knowledge_source_sync"
LEASE_SECONDS = 300
POLL_SECONDS = 2.0


class KnowledgeSourceSyncTaskService:
    """Coordinates durable sync commands without running work in API requests."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)

    async def enqueue(self, source_id: int) -> TaskRecord:
        """Persist one idempotent queued command for a knowledge source."""
        source = await KnowledgeSourceSyncService(self._session).source_service.get(
            source_id
        )
        if not source.enabled:
            raise ConflictError("Disabled knowledge source cannot be synchronized")
        key = f"knowledge_source_sync:{source_id}"
        active = await self._tasks.find_active_by_key(key)
        if active is not None:
            return active
        return await self._tasks.create(
            TaskRecord(
                task_type=TASK_TYPE,
                title=f"Synchronize knowledge source {source.id}",
                status=TaskStatus.QUEUED.value,
                progress=0,
                source_type="knowledge_source",
                source_id=source.id,
                detail_json=json.dumps({}, ensure_ascii=False),
                idempotency_key=key,
            )
        )


class KnowledgeSourceSyncWorker:
    """Explicit worker process adapter that claims persistent sync tasks by lease."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], worker_id: str | None = None
    ) -> None:
        self._sessions = sessions
        self._worker_id = worker_id or f"sync-worker-{uuid4().hex}"

    async def run_once(self) -> bool:
        """Claim and execute one task; callers provide process supervision and polling."""
        async with self._sessions() as session:
            tasks = TaskRepository(session)
            task = await tasks.claim_next(self._worker_id, LEASE_SECONDS)
            if task is None:
                await session.commit()
                return False
            await session.commit()
        async with self._sessions() as session:
            tasks = TaskRepository(session)
            task = await tasks.get(task.id)
            if task is None or task.source_id is None:
                raise NotFoundError("Sync task is missing its knowledge source")
            source_id = task.source_id
            try:
                heartbeat_stop = asyncio.Event()

                async def execute_sync() -> KnowledgeSourceSyncSummary:
                    try:
                        return await KnowledgeSourceSyncService(session).sync(
                            source_id
                        )
                    finally:
                        heartbeat_stop.set()

                async with asyncio.TaskGroup() as task_group:
                    execution = task_group.create_task(execute_sync())
                    task_group.create_task(
                        self._heartbeat(task.id, heartbeat_stop),
                        name=f"knowledge-source-sync-heartbeat-{task.id}",
                    )
                summary = execution.result()
            except Exception:
                logger.exception(
                    "knowledge_source_sync_task_failed task_id=%s", task.id
                )
                await tasks.finish(
                    task,
                    TaskStatus.FAILED,
                    "{}",
                    "sync_failed",
                    "Knowledge source synchronization failed",
                )
                await session.commit()
                return True
            await tasks.finish(
                task,
                TaskStatus.SUCCEEDED,
                summary.model_dump_json(),
            )
            await session.commit()
            return True

    async def run(
        self, stop_event: asyncio.Event, poll_seconds: float = POLL_SECONDS
    ) -> None:
        """Poll durable work until process supervision requests shutdown."""
        while not stop_event.is_set():
            has_processed = await self.run_once()
            if has_processed:
                continue
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
            except TimeoutError:
                continue

    async def _heartbeat(self, task_id: int, stop_event: asyncio.Event) -> None:
        """Keep an owned lease alive while the sync operation is still executing."""
        interval = max(1.0, LEASE_SECONDS / 3)
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                return
            except TimeoutError:
                pass
            async with self._sessions() as session:
                is_owned = await TaskRepository(session).renew_lease(
                    task_id, self._worker_id, LEASE_SECONDS
                )
                await session.commit()
            if not is_owned:
                logger.warning(
                    "knowledge_source_sync_lease_lost task_id=%s", task_id
                )
                return
