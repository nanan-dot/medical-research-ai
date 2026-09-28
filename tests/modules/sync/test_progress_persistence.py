"""行为测试：同步进度节流但保留阶段转换。"""

import pytest

pytest_plugins = ["tests.modules.knowledge_source.test_service"]

from app.modules.knowledge_source.sync_progress import SyncPhase, calculate_progress
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus


@pytest.mark.asyncio
async def test_progress_writes_are_throttled_by_percentage(session) -> None:
    """AC-PROGRESS-06：相同百分点的文件处理不重复写库，阶段切换仍被记录。"""
    task = await TaskRepository(session).create(
        TaskRecord(
            task_type="knowledge_source_sync",
            title="sync",
            status=TaskStatus.RUNNING.value,
            progress=0,
            detail_json="{}",
        )
    )
    repository = TaskRepository(session)
    await repository.update_sync_progress(
        task, calculate_progress(SyncPhase.PERSISTING, 1, 200)
    )
    first_updated_at = task.progress_updated_at
    await repository.update_sync_progress(
        task, calculate_progress(SyncPhase.PERSISTING, 2, 200)
    )
    assert task.progress_updated_at == first_updated_at
    await repository.update_sync_progress(
        task, calculate_progress(SyncPhase.PARSING, 2, 200)
    )
    assert task.phase == SyncPhase.PARSING.value
