"""Literature-search endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.schema import (
    BuildQueryRequest,
    BuildQueryResponse,
    ExpandTermsRequest,
    ExpandTermsResponse,
    LiteratureSearchResultRead,
    LiteratureSearchTaskCreate,
    LiteratureSearchTaskList,
    LiteratureSearchTaskRead,
    LiteratureSearchTaskRerun,
    ParseQueryRequest,
    ParseQueryResponse,
    SearchExecuteRequest,
    SearchStrategyExport,
)
from app.modules.literature_search.service import LiteratureSearchService

router = APIRouter(prefix="/literature-search", tags=["Literature search"])


# ----------------------------------------------------------------------
# 检索任务与历史（R2-WP04）
# ----------------------------------------------------------------------


@router.get("", response_model=LiteratureSearchTaskList)
async def list_tasks(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchTaskList:
    """分页返回检索任务历史（创建时间倒序）。"""
    return await LiteratureSearchService(session).list_tasks(offset=offset, limit=limit)


@router.post("", response_model=LiteratureSearchTaskRead, status_code=201)
async def create_task(
    request: LiteratureSearchTaskCreate,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchTaskRead:
    """创建检索任务并立即执行，返回任务详情（含版本时间线）。"""
    return await LiteratureSearchService(session).create_task(request)


@router.post("/{id}/rerun", response_model=LiteratureSearchTaskRerun)
async def rerun_task(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchTaskRerun:
    """按持久化输入快照重跑任务，创建新结果版本并返回变化摘要。"""
    return await LiteratureSearchService(session).rerun_task(id)


@router.get("/{id}/strategy", response_model=SearchStrategyExport)
async def export_strategy(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> SearchStrategyExport:
    """导出 PRISMA-compliant 检索策略（数据库、检索日期、查询串、结果数）。"""
    return await LiteratureSearchService(session).export_strategy(id)


@router.get("/{id}", response_model=LiteratureSearchTaskRead)
async def get_task(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchTaskRead:
    """返回单个检索任务详情（含全部结果版本）。"""
    return await LiteratureSearchService(session).get_task(id)


# ----------------------------------------------------------------------
# 检索过程构建（WP01/WP02 能力）
# ----------------------------------------------------------------------


@router.post("/parse-query", response_model=ParseQueryResponse)
async def parse_query(
    request: ParseQueryRequest,
    session: AsyncSession = Depends(get_session),
) -> ParseQueryResponse:
    return await LiteratureSearchService(session).parse_query(request.raw_topic)


@router.post("/expand-terms", response_model=ExpandTermsResponse)
async def expand_terms(
    request: ExpandTermsRequest,
    session: AsyncSession = Depends(get_session),
) -> ExpandTermsResponse:
    return await LiteratureSearchService(session).expand_terms(request.candidate, request.user_edits)


@router.post("/build-query", response_model=BuildQueryResponse)
async def build_query(request: BuildQueryRequest) -> BuildQueryResponse:
    result = LiteratureSearchService.build_query(request.term_groups)
    return BuildQueryResponse(**result.model_dump(), user_edits=request.user_edits)


@router.post("/execute", response_model=LiteratureSearchResultRead)
async def execute_search(
    request: SearchExecuteRequest,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchResultRead:
    return await LiteratureSearchService(session).execute_search(request)


@router.get("/{id}/results", response_model=LiteratureSearchResultRead)
async def get_search_result(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchResultRead:
    return await LiteratureSearchService(session).get_result(id)


@router.get("/{id}/bibtex", response_class=PlainTextResponse)
async def export_bibtex(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> str:
    return await LiteratureSearchService(session).bibtex(id)
