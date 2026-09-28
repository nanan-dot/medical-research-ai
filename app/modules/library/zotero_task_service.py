"""Durable, cancellable Zotero synchronization commands and worker adapter."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.sync_progress import SyncPhase
from app.modules.library.model import ZoteroLibrary
from app.modules.library.zotero import ZoteroAdapter
from app.modules.library.zotero_service import ZoteroSyncService
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus

logger = logging.getLogger(__name__)
TASK_TYPE = "zotero_sync"
LEASE_SECONDS = 300


class ZoteroSyncTaskService:
    """Persist one idempotent sync request per Zotero source."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)

    async def enqueue(self, source_id: int, trigger: str = "manual") -> TaskRecord:
        source = await self._session.get(KnowledgeSource, source_id)
        if source is None or source.source_type != "zotero_library":
            raise NotFoundError("Zotero source not found")
        if not source.enabled:
            raise ConflictError("Disabled Zotero source cannot be synchronized")
        key = f"zotero_sync:{source_id}"
        active = await self._tasks.find_active_by_key(key)
        if active is not None:
            return active
        try:
            async with self._session.begin_nested():
                return await self._tasks.create(
                    TaskRecord(
                        task_type=TASK_TYPE,
                        title=f"Synchronize Zotero library {source.name}",
                        status=TaskStatus.QUEUED.value,
                        progress=0,
                        phase=SyncPhase.QUEUED.value,
                        source_type="zotero_library",
                        source_id=source_id,
                        detail_json=json.dumps({"trigger": trigger}, ensure_ascii=False),
                        idempotency_key=key,
                        active_idempotency_key=key,
                    )
                )
        except IntegrityError:
            active = await self._tasks.find_active_by_key(key)
            if active is None:
                raise
            return active


class ZoteroSyncWorker:
    """Worker that keeps I/O at the official API boundary, not in repositories."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], worker_id: str | None = None
    ) -> None:
        self._sessions = sessions
        self._worker_id = worker_id or f"zotero-worker-{uuid4().hex}"

    async def run_once(self) -> bool:
        async with self._sessions() as session:
            tasks = TaskRepository(session)
            task = await tasks.claim_next(self._worker_id, LEASE_SECONDS, TASK_TYPE)
            if task is None:
                await session.commit()
                return False
            await session.commit()

        async with self._sessions() as session:
            tasks = TaskRepository(session)
            task = await tasks.get(task.id)
            if task is None or task.source_id is None:
                raise NotFoundError("Zotero sync task is missing its source")
            try:
                library = await session.scalar(
                    select(ZoteroLibrary).where(
                        ZoteroLibrary.knowledge_source_id == task.source_id
                    )
                )
                if library is None:
                    raise NotFoundError("Zotero source not found")
                async with httpx.AsyncClient() as client:
                    adapter = ZoteroAdapter(
                        settings.ZOTERO_API_KEY,
                        library.library_type,
                        library.library_id,
                        client=client,
                        base_url=settings.ZOTERO_API_BASE_URL,
                        max_retries=settings.ZOTERO_MAX_RETRIES,
                        timeout_seconds=settings.ZOTERO_TIMEOUT_SECONDS,
                    )
                    summary = await ZoteroSyncService(session).sync(
                        task.source_id,
                        lambda: adapter.fetch_incremental(
                            int(library.version_cursor)
                            if library.version_cursor and library.version_cursor.isdigit()
                            else None
                        ),
                        adapter.fetch_attachment,
                    )
            except Exception as exc:
                logger.exception("zotero_sync_task_failed task_id=%s", task.id)
                code = getattr(exc, "code", "zotero_sync_failed")
                await tasks.finish(
                    task,
                    TaskStatus.FAILED,
                    "{}",
                    code,
                    "Zotero synchronization failed",
                )
                await session.commit()
                return True
            await tasks.finish(
                task,
                TaskStatus.SUCCEEDED,
                json.dumps(summary, ensure_ascii=False),
            )
            await session.commit()
            return True
