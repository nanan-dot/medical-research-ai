"""统一任务中心的数据访问层。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.task.model import TaskRecord
from app.modules.task.schema import TaskStatus


class TaskRepository:
    """隔离任务记录的数据库查询与持久化。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
