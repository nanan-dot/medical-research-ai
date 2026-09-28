"""行为测试：自动同步的调度声明与持久化任务投递。"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest_plugins = ["tests.modules.knowledge_source.test_service"]

from app.modules.knowledge_source.auto_sync_scheduler import (
    KnowledgeSourceAutoSyncScheduler,
)
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceType,
    KnowledgeSourceUpdate,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.sync_task_service import (
    KnowledgeSourceSyncTaskService,
)
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus


@pytest.mark.asyncio
async def test_due_auto_sync_is_claimed_once_and_creates_persistent_task(session, tmp_path: Path) -> None:
    """AC-AUTO-01/02/03：到期且启用的来源只会被一次条件更新声明。"""
    root = tmp_path / "source"
    root.mkdir()
    service = KnowledgeSourceService(session)
    source = await service.create(KnowledgeSourceCreate(name="source", source_type=KnowledgeSourceType.LOCAL_FOLDER, root_path=str(root)))
    await service.update(source.id, KnowledgeSourceUpdate(auto_sync=True, sync_interval_minutes=5))
    entity = await service.repo.get(source.id)
    assert entity is not None
    now = datetime.now(UTC)
    entity.next_auto_sync_at = now - timedelta(seconds=1)
    await session.flush()

    first = await KnowledgeSourceAutoSyncScheduler(session).enqueue_due_sources(now)
    second = await KnowledgeSourceAutoSyncScheduler(session).enqueue_due_sources(now)
    assert first == [source.id]
    assert second == []
    task = await TaskRepository(session).find_active_by_key(f"knowledge_source_sync:{source.id}")
    assert task is not None
    assert task.detail_json == '{"trigger": "auto"}'


@pytest.mark.asyncio
async def test_auto_sync_enqueue_failure_records_backoff(
    session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-AUTO-06：投递异常必须保留失败次数并计算下一次退避时间。"""
    root = tmp_path / "failing-source"
    root.mkdir()
    service = KnowledgeSourceService(session)
    source = await service.create(
        KnowledgeSourceCreate(
            name="failing-source",
            source_type=KnowledgeSourceType.LOCAL_FOLDER,
            root_path=str(root),
        )
    )
    await service.update(source.id, KnowledgeSourceUpdate(auto_sync=True, sync_interval_minutes=5))
    entity = await service.repo.get(source.id)
    assert entity is not None
    now = datetime.now(UTC)
    entity.next_auto_sync_at = now - timedelta(seconds=1)
    await session.flush()

    async def raise_enqueue(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("test enqueue failure")

    monkeypatch.setattr(KnowledgeSourceSyncTaskService, "enqueue", raise_enqueue)
    assert await KnowledgeSourceAutoSyncScheduler(session).enqueue_due_sources(now) == []
    assert entity.auto_sync_failure_count == 1
    assert entity.next_auto_sync_at == now + timedelta(minutes=10)


@pytest.mark.asyncio
async def test_active_idempotency_key_is_unique(session) -> None:
    """AC-AUTO-02：数据库而非调用顺序保证活动任务只有一条。"""
    from sqlalchemy.exc import IntegrityError

    from app.modules.task.model import TaskRecord

    repository = TaskRepository(session)
    active_key = "knowledge_source_sync:99"
    await repository.create(
        TaskRecord(
            task_type="knowledge_source_sync",
            title="first",
            status=TaskStatus.QUEUED.value,
            progress=0,
            detail_json="{}",
            idempotency_key=active_key,
            active_idempotency_key=active_key,
        )
    )
    with pytest.raises(IntegrityError):
        await repository.create(
            TaskRecord(
                task_type="knowledge_source_sync",
                title="duplicate",
                status=TaskStatus.QUEUED.value,
                progress=0,
                detail_json="{}",
                idempotency_key=active_key,
                active_idempotency_key=active_key,
            )
        )
