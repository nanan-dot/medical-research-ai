"""统一任务中心 HTTP API。"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.core.database import get_session
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskCreate, TaskPage, TaskRead, TaskStatus
from app.modules.task.service import TaskService

router = APIRouter(prefix="/tasks", tags=["任务中心"])


def _service(session: AsyncSession) -> TaskService:
    """为每个请求创建绑定当前数据库会话的任务服务。"""
    return TaskService(TaskRepository(session))


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, session: AsyncSession = Depends(get_session)
) -> TaskRead:
    """创建待执行任务记录。"""
    return await _service(session).create(payload)


@router.get("", response_model=TaskPage)
async def list_tasks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> TaskPage:
    """按状态筛选并分页读取任务。"""
    return await _service(session).list(offset, limit, task_status)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int, session: AsyncSession = Depends(get_session)
) -> TaskRead:
    """读取单个任务详情。"""
    return await _service(session).get(task_id)


@router.post("/{task_id}/cancel", response_model=TaskRead)
async def cancel_task(task_id: int, session: AsyncSession = Depends(get_session)) -> TaskRead:
    try:
        return await _service(session).cancel(task_id)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc


@router.post("/{task_id}/retry", response_model=TaskRead)
async def retry_task(task_id: int, session: AsyncSession = Depends(get_session)) -> TaskRead:
    try:
        return await _service(session).retry(task_id)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc
