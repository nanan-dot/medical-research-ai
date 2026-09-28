"""统一任务中心的数据访问层。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_source.sync_progress import SyncProgress, completed_progress
from app.modules.task.model import TaskRecord
from app.modules.task.schema import TaskStatus

MIN_PROGRESS_PERSIST_DELTA = 1


class TaskRepository:
    """隔离任务记录的数据库查询与持久化。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def create(self, task: TaskRecord) -> TaskRecord:
        """写入并刷新新建任务。"""
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def get(self, task_id: int) -> TaskRecord | None:
        """按主键读取单个任务。"""
        result = await self._session.execute(
            select(TaskRecord).where(TaskRecord.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self, offset: int, limit: int, status: TaskStatus | None
    ) -> list[TaskRecord]:
        """按创建时间倒序读取任务页。"""
        statement = select(TaskRecord).order_by(TaskRecord.created_at.desc())
        if status is not None:
            statement = statement.where(TaskRecord.status == status.value)
        result = await self._session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(self, status: TaskStatus | None) -> int:
        """计算符合当前筛选条件的任务数量。"""
        statement = select(func.count()).select_from(TaskRecord)
        if status is not None:
            statement = statement.where(TaskRecord.status == status.value)
        return int((await self._session.execute(statement)).scalar_one())

    async def find_active_by_key(self, key: str) -> TaskRecord | None:
        """Find one queued/running task for an idempotent business operation."""
        result = await self._session.execute(
            select(TaskRecord).where(
                TaskRecord.idempotency_key == key,
                TaskRecord.status.in_(
                    (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def claim_next(
        self,
        worker_id: str,
        lease_seconds: int,
        task_type: str = "knowledge_source_sync",
    ) -> TaskRecord | None:
        """Atomically claim queued or abandoned work using a database lease."""
        now = datetime.now(UTC)
        candidate = await self._session.scalar(
            select(TaskRecord.id)
            .where(
                TaskRecord.task_type == task_type,
                or_(
                    TaskRecord.status == TaskStatus.QUEUED.value,
                    and_(
                        TaskRecord.status == TaskStatus.RUNNING.value,
                        TaskRecord.lease_expires_at < now,
                    ),
                ),
            )
            .order_by(TaskRecord.created_at, TaskRecord.id)
            .limit(1)
        )
        if candidate is None:
            return None
        expires_at = now + timedelta(seconds=lease_seconds)
        result = await self._session.execute(
            update(TaskRecord)
            .where(
                TaskRecord.id == candidate,
                or_(
                    TaskRecord.status == TaskStatus.QUEUED.value,
                    and_(
                        TaskRecord.status == TaskStatus.RUNNING.value,
                        TaskRecord.lease_expires_at < now,
                    ),
                ),
            )
            .values(
                status=TaskStatus.RUNNING.value,
                lease_owner=worker_id,
                lease_expires_at=expires_at,
                heartbeat_at=now,
                started_at=func.coalesce(TaskRecord.started_at, now),
                retry_count=TaskRecord.retry_count + 1,
            )
        )
        if getattr(result, "rowcount", 0) != 1:
            return None
        return await self.get(int(candidate))

    async def finish(
        self,
        task: TaskRecord,
        status: TaskStatus,
        detail_json: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> TaskRecord:
        """Persist the terminal task state and release its lease."""
        task.status = status.value
        if status == TaskStatus.SUCCEEDED:
            completion = completed_progress()
            task.progress = completion.progress_percent or 0
            task.phase = completion.phase.value
            task.completed_units = completion.completed_units
            task.total_units = completion.total_units
            task.current_item = None
            task.progress_updated_at = datetime.now(UTC)
        task.detail_json = detail_json
        task.error_code = error_code
        task.error_message = error_message
        task.lease_owner = None
        task.active_idempotency_key = None
        task.lease_expires_at = None
        task.heartbeat_at = datetime.now(UTC)
        task.finished_at = datetime.now(UTC)
        await self._session.flush()
        return task

    async def update_sync_progress(
        self, task: TaskRecord, progress: SyncProgress
    ) -> None:
        """写入真实进度；拒绝倒退以抵御乱序 Worker 心跳。"""
        has_new_phase = progress.phase.value != task.phase
        has_indeterminate_progress = (
            progress.progress_percent is None and task.total_units is not None
        )
        has_meaningful_progress = (
            progress.progress_percent is not None
            and progress.progress_percent - task.progress >= MIN_PROGRESS_PERSIST_DELTA
        )
        if (
            progress.completed_units < task.completed_units
            or not (has_new_phase or has_indeterminate_progress or has_meaningful_progress)
        ):
            return
        task.phase = progress.phase.value
        task.completed_units = progress.completed_units
        task.total_units = progress.total_units
        task.current_item = progress.current_item
        if progress.progress_percent is not None:
            task.progress = max(task.progress, progress.progress_percent)
        task.progress_updated_at = datetime.now(UTC)
        await self._session.flush()

    async def renew_lease(
        self, task_id: int, worker_id: str, lease_seconds: int
    ) -> bool:
        """Extend a running task lease only when the caller still owns it."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(TaskRecord)
            .where(
                TaskRecord.id == task_id,
                TaskRecord.status == TaskStatus.RUNNING.value,
                TaskRecord.lease_owner == worker_id,
                TaskRecord.lease_expires_at > now,
            )
            .values(
                heartbeat_at=now,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
            )
        )
        return getattr(result, "rowcount", 0) == 1
