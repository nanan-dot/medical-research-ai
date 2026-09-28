"""HTTP boundary for versioned core reading plans."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.reading_plan.schema import (
    CandidatePage,
    ManualItemCreate,
    PlanGenerateRequest,
    PlanItemPatch,
    PromoteCoreRequest,
    ReadingPlanRead,
    ReadingPlanVersionPage,
    StageOrderRequest,
)
from app.modules.reading_plan.service import ReadingPlanService

router = APIRouter(prefix="/literature-search/results/{result_id}/reading-plans", tags=["Core reading plans"])

@router.post("", response_model=ReadingPlanRead, status_code=201)
async def create_plan(result_id: int, request: PlanGenerateRequest, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).generate(result_id, request)

@router.get("", response_model=ReadingPlanVersionPage)
async def list_plans(result_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), session: AsyncSession = Depends(get_session)) -> ReadingPlanVersionPage:
    return await ReadingPlanService(session).list_versions(result_id, limit, offset)

@router.get("/active", response_model=ReadingPlanRead)
async def active_plan(result_id: int, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).active(result_id)

@router.get("/{plan_id}", response_model=ReadingPlanRead)
async def get_plan(result_id: int, plan_id: int, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).get(result_id, plan_id)

@router.post("/{plan_id}/replan", response_model=ReadingPlanRead, status_code=201)
async def replan(result_id: int, plan_id: int, request: PlanGenerateRequest, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).replan(result_id, plan_id, request)

@router.patch("/{plan_id}/items/{pmid}", response_model=ReadingPlanRead)
async def patch_item(result_id: int, plan_id: int, pmid: str, request: PlanItemPatch, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).patch_item(result_id, plan_id, pmid, request)

@router.post("/{plan_id}/items", response_model=ReadingPlanRead, status_code=201)
async def add_item(result_id: int, plan_id: int, request: ManualItemCreate, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).add_manual(result_id, plan_id, request)

@router.delete("/{plan_id}/items/{pmid}", response_model=ReadingPlanRead)
async def delete_item(result_id: int, plan_id: int, pmid: str, force: bool = False, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).delete_item(result_id, plan_id, pmid, force)

@router.put("/{plan_id}/stages/{stage}/order", response_model=ReadingPlanRead)
async def save_stage_order(result_id: int, plan_id: int, stage: str, request: StageOrderRequest, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).save_order(result_id, plan_id, stage, request.pmids)

@router.get("/{plan_id}/stages/{stage}/candidates", response_model=CandidatePage)
async def stage_candidates(result_id: int, plan_id: int, stage: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = None, year: int | None = Query(None, ge=1900, le=2100), publication_type: str | None = None, jcr_quartile: str | None = None, wos_index: str | None = None, cas_quartile: str | None = None, impact_factor_min: float | None = Query(None, ge=0), session: AsyncSession = Depends(get_session)) -> CandidatePage:
    return await ReadingPlanService(session).candidates(result_id, plan_id, stage, page, page_size, search, year, publication_type, jcr_quartile, wos_index, cas_quartile, impact_factor_min)

@router.post("/{plan_id}/stages/{stage}/core", response_model=ReadingPlanRead)
async def promote_core(result_id: int, plan_id: int, stage: str, request: PromoteCoreRequest, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).promote(result_id, plan_id, stage, request)

@router.delete("/{plan_id}/stages/{stage}/core/{pmid}", response_model=ReadingPlanRead)
async def demote_core(result_id: int, plan_id: int, stage: str, pmid: str, session: AsyncSession = Depends(get_session)) -> ReadingPlanRead:
    return await ReadingPlanService(session).demote(result_id, plan_id, stage, pmid)

@router.get("/{plan_id}/export")
async def export_plan(result_id: int, plan_id: int, format: str = "csv", session: AsyncSession = Depends(get_session)) -> Response:
    content, media_type = await ReadingPlanService(session).export(result_id, plan_id, format)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="reading-plan-{plan_id}.{format}"'})
