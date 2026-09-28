"""Result-scoped recommendation V5 API."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.recommendation.v5_scheduler import RecommendationScheduler
from app.modules.recommendation.v5_schema import (
    DecisionRead,
    DismissRequest,
    RecommendationItemRead,
    RecommendationPage,
    RecommendationRunCreate,
    RecommendationRunRead,
    RecommendationStatusRead,
)
from app.modules.recommendation.v5_service import RecommendationV5Service

router = APIRouter(
    prefix="/literature-search/{result_id}/recommendations",
    tags=["Literature recommendations"],
)


@router.post("/runs", response_model=RecommendationRunRead, status_code=202)
async def create_run(
    result_id: int,
    request: RecommendationRunCreate,
    session: AsyncSession = Depends(get_session),
) -> RecommendationRunRead:
    response = await RecommendationV5Service(session).queue_run(result_id, request)
    await session.commit()
    if response.operation == "created":
        RecommendationScheduler.schedule(response.run_id)
    return response


@router.get("/status", response_model=RecommendationStatusRead)
async def get_status(
    result_id: int, session: AsyncSession = Depends(get_session)
) -> RecommendationStatusRead:
    return await RecommendationV5Service(session).status(result_id)


@router.post("/cancel", response_model=RecommendationRunRead)
async def cancel_run(
    result_id: int, session: AsyncSession = Depends(get_session)
) -> RecommendationRunRead:
    response = await RecommendationV5Service(session).cancel(result_id)
    await session.commit()
    return response


@router.get("/active", response_model=RecommendationPage)
async def get_active(
    result_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Literal["priority", "created"] = "priority",
    overlap: Literal["novel", "covered"] = "novel",
    session: AsyncSession = Depends(get_session),
) -> RecommendationPage:
    return await RecommendationV5Service(session).page(
        result_id, page=page, page_size=page_size, sort=sort, overlap=overlap
    )


@router.get("/runs", response_model=list[RecommendationRunRead])
async def list_runs(
    result_id: int, session: AsyncSession = Depends(get_session)
) -> list[RecommendationRunRead]:
    return await RecommendationV5Service(session).list_runs(result_id)


@router.get("/runs/{run_id}", response_model=RecommendationRunRead)
async def get_run(
    result_id: int, run_id: int, session: AsyncSession = Depends(get_session)
) -> RecommendationRunRead:
    return await RecommendationV5Service(session).get_run(result_id, run_id)


@router.get(
    "/runs/{run_id}/items/{pmid}/explanation", response_model=RecommendationItemRead
)
async def explanation(
    result_id: int, run_id: int, pmid: str, session: AsyncSession = Depends(get_session)
) -> RecommendationItemRead:
    return await RecommendationV5Service(session).explanation(result_id, run_id, pmid)


@router.post("/runs/{run_id}/items/{pmid}/accept", response_model=DecisionRead)
async def accept(
    result_id: int, run_id: int, pmid: str, session: AsyncSession = Depends(get_session)
) -> DecisionRead:
    response = await RecommendationV5Service(session).decide(
        result_id, run_id, pmid, "accepted"
    )
    await session.commit()
    return response


@router.post("/runs/{run_id}/items/{pmid}/dismiss", response_model=DecisionRead)
async def dismiss(
    result_id: int,
    run_id: int,
    pmid: str,
    request: DismissRequest,
    session: AsyncSession = Depends(get_session),
) -> DecisionRead:
    response = await RecommendationV5Service(session).decide(
        result_id, run_id, pmid, "dismissed", request
    )
    await session.commit()
    return response
