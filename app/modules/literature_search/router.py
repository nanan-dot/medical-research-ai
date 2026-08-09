"""Literature-search endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.schema import (
    BuildQueryRequest,
    BuildQueryResponse,
    DuplicateGroupList,
    DuplicateGroupRead,
    DuplicateResolveRequest,
    ExpandTermsRequest,
    ExpandTermsResponse,
    ItemStateRead,
    ItemStateUpdate,
    LiteratureSearchResultPage,
    LiteratureSearchResultRead,
    LiteratureSearchTaskCreate,
    LiteratureSearchTaskList,
    LiteratureSearchTaskRead,
    LiteratureSearchTaskRerun,
    ParseQueryRequest,
    ParseQueryResponse,
    ReadingOrderRead,
    ReadingOrderRequest,
    ReadingOrderSaveRequest,
    ResultQueryParams,
    SearchExecuteRequest,
    SearchStrategyExport,
)
from app.modules.literature_search.service import LiteratureSearchService

router = APIRouter(prefix="/literature-search", tags=["Literature search"])
duplicate_group_router = APIRouter(
    prefix="/duplicate-groups", tags=["Literature deduplication"]
)


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
    return await LiteratureSearchService(session).expand_terms(
        request.candidate, request.user_edits
    )


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


@router.get("/{id}/results", response_model=LiteratureSearchResultPage)
async def get_search_results(
    id: int,
    params: ResultQueryParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> LiteratureSearchResultPage:
    """分页返回检索结果，支持筛选、排序与排序理由。

    params 为白名单 query 参数（ResultQueryParams），未知参数由 FastAPI
    忽略；page 越界时 items 为空。响应中每个条目携带 sort_reason（排序理由）
    与 state（已保存/已读/标签用户态）。
    """
    return await LiteratureSearchService(session).get_result_page(id, params)


@router.patch("/{id}/items/{pmid}/state", response_model=ItemStateRead)
async def update_item_state(
    id: int,
    pmid: str,
    request: ItemStateUpdate,
    session: AsyncSession = Depends(get_session),
) -> ItemStateRead:
    """写入单条结果的用户态（saved / read_status / tags / 自定义排序序号）。"""
    return await LiteratureSearchService(session).update_item_state(id, pmid, request)


@router.get("/{id}/items/{pmid}/state", response_model=ItemStateRead)
async def get_item_state(
    id: int,
    pmid: str,
    session: AsyncSession = Depends(get_session),
) -> ItemStateRead:
    """读取单条结果的用户态；从未写入过时返回默认值。"""
    return await LiteratureSearchService(session).get_item_state(id, pmid)


@router.get("/{id}/bibtex", response_class=PlainTextResponse)
async def export_bibtex(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> str:
    return await LiteratureSearchService(session).bibtex(id)


@router.post("/{id}/deduplicate", response_model=DuplicateGroupList)
async def deduplicate_task(
    id: int, session: AsyncSession = Depends(get_session)
) -> DuplicateGroupList:
    """对指定任务及各任务当前快照生成可解释、可撤销的去重决策。"""
    return await LiteratureSearchService(session).deduplicate_task(id)


@duplicate_group_router.get("", response_model=DuplicateGroupList)
async def list_duplicate_groups(
    session: AsyncSession = Depends(get_session),
) -> DuplicateGroupList:
    return await LiteratureSearchService(session).list_duplicate_groups()


@duplicate_group_router.post("/{id}/resolve", response_model=DuplicateGroupRead)
async def resolve_duplicate_group(
    id: int,
    request: DuplicateResolveRequest,
    session: AsyncSession = Depends(get_session),
) -> DuplicateGroupRead:
    return await LiteratureSearchService(session).resolve_duplicate_group(id, request)


# ----------------------------------------------------------------------
# 推荐阅读顺序（R2-WP08）
# ----------------------------------------------------------------------


@router.post("/{id}/reading-order", response_model=ReadingOrderRead)
async def generate_reading_order(
    id: int,
    request: ReadingOrderRequest,
    session: AsyncSession = Depends(get_session),
) -> ReadingOrderRead:
    """生成基于规则特征的分层阅读顺序。

    manual_order（可选）为用户已保存的人工顺序：携带时优先应用，保证
    "重新生成不覆盖人工顺序"；不携带则使用算法顺序或库中已保存顺序。
    """
    return await LiteratureSearchService(session).generate_reading_order(
        id, request.manual_order
    )


@router.put("/{id}/reading-order/order", response_model=ReadingOrderRead)
async def save_reading_order(
    id: int,
    request: ReadingOrderSaveRequest,
    session: AsyncSession = Depends(get_session),
) -> ReadingOrderRead:
    """保存用户拖拽后的人工顺序（完整 PMID 列表，全量替换）。

    保存后返回应用该人工顺序的阅读顺序（order_source="manual"）。
    """
    return await LiteratureSearchService(session).save_reading_order(
        id, request.manual_order
    )
