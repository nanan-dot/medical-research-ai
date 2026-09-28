"""持久化自动同步调度器；只投递，不执行文件扫描。"""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.sync_task_service import (
    KnowledgeSourceSyncTaskService,
)

logger = logging.getLogger(__name__)


class KnowledgeSourceAutoSyncScheduler:
    """使用数据库条件更新声明调度权，支持多个调度进程并存。"""

    def __init__(self, session: AsyncSession) -> None:
        self._sources = KnowledgeSourceRepository(session)
        self._tasks = KnowledgeSourceSyncTaskService(session)

    async def enqueue_due_sources(self, now: datetime | None = None) -> list[int]:
        """为当前到期来源创建或复用持久化同步任务。"""
        scheduled_at = now or datetime.now(UTC)
        source_ids = await self._sources.due_auto_sync_ids(scheduled_at)
        enqueued: list[int] = []
        for source_id in source_ids:
            source = await self._sources.claim_auto_sync(source_id, scheduled_at)
            if source is None:
                continue
            try:
                await self._tasks.enqueue(source.id, trigger="auto")
            except Exception:
                logger.exception("knowledge_source_auto_sync_enqueue_failed source_id=%s", source.id)
                await self._sources.record_auto_sync_enqueue_failure(source, scheduled_at)
                continue
            enqueued.append(source.id)
        return enqueued
