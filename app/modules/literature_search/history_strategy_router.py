from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.history_strategy_schema import *
from app.modules.literature_search.history_strategy_service import StrategyService

router = APIRouter(prefix="/literature-search/history-strategies", tags=["检索策略"])


@router.get("", response_model=StrategyPage)
async def list_strategies(
    q: str | None = None,
    archived: bool = False,
    research_context_id: int | None = None,
    framework: str | None = None,
    created_from: datetime | None = None,
    has_changes: bool | None = None,
    execution_status: ExecutionStatusFilter | None = None,
    sort: StrategySort = "updated_at",
    offset: int = 0,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await StrategyService(session).list(
        query=q,
        archived=archived,
        research_context_id=research_context_id,
        framework=framework,
        created_from=created_from,
        has_changes=has_changes,
        execution_status=execution_status,
        sort=sort,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=StrategyRead, status_code=201)
async def create_strategy(
    request: StrategyCreate, session: AsyncSession = Depends(get_session)
):
    return await StrategyService(session).create(request)


@router.post(
    "/{id}/versions/{version}/executions",
    response_model=ExecutionRead,
    status_code=201,
)
async def execute_strategy_version(
    id: int,
    version: int,
    request: StrategyExecuteRequest,
    session: AsyncSession = Depends(get_session),
) -> ExecutionRead:
    """按指定策略版本的持久化检索式执行，并保存独立执行历史。"""
    return await StrategyService(session).execute_version(id, version, request)


@router.get("/export/all", response_model=StrategyExportRead)
async def export_strategies(session: AsyncSession = Depends(get_session)):
    return await StrategyService(session).export()


@router.get("/{id}", response_model=StrategyRead)
async def get_strategy(id: int, session: AsyncSession = Depends(get_session)):
    return await StrategyService(session).detail(id)


@router.patch("/{id}", response_model=StrategyRead)
async def patch_strategy(
    id: int, request: StrategyPatch, session: AsyncSession = Depends(get_session)
):
    return await StrategyService(session).patch(id, request)


@router.post("/{id}/versions", response_model=StrategyRead)
async def create_version(
    id: int,
    request: StrategyVersionCreate,
    session: AsyncSession = Depends(get_session),
):
    return await StrategyService(session).add_version(id, request)


@router.get("/{id}/versions/{a}/compare/{b}", response_model=StrategyCompareRead)
async def compare_versions(
    id: int, a: int, b: int, session: AsyncSession = Depends(get_session)
):
    return await StrategyService(session).compare(id, a, b)


@router.post("/{id}/clone", response_model=StrategyRead, status_code=201)
async def clone_strategy(
    id: int, request: StrategyCloneRequest, session: AsyncSession = Depends(get_session)
):
    return await StrategyService(session).clone(id, request.name)


@router.post("/{id}/archive", response_model=StrategyRead)
async def archive_strategy(id: int, session: AsyncSession = Depends(get_session)):
    return await StrategyService(session).archive(id, True)


@router.post("/{id}/restore", response_model=StrategyRead)
async def restore_strategy(id: int, session: AsyncSession = Depends(get_session)):
    return await StrategyService(session).archive(id, False)
