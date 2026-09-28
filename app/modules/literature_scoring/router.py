"""HTTP boundary for scoring lifecycle endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_scoring.scheduler import LiteratureScoringScheduler
from app.modules.literature_scoring.schema import (
    ResearchIntentSnapshotCreate,
    ScoreExplanationRead,
    ScoringRunCreate,
    ScoringRunRead,
    ScoringStatusRead,
)
from app.modules.literature_scoring.service import LiteratureScoringService

router = APIRouter(prefix="/literature-search", tags=["Literature scoring"])


@router.post("/research-intents", status_code=201)
async def create_research_intent(
    request: ResearchIntentSnapshotCreate, session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    return {"id": await LiteratureScoringService(session).create_intent(request)}


@router.post("/{result_id}/scoring/runs", response_model=ScoringRunRead)
async def create_scoring_run(
    result_id: int,
    request: ScoringRunCreate,
    session: AsyncSession = Depends(get_session),
) -> ScoringRunRead:
    run = await LiteratureScoringService(session).queue_run(result_id, request)
    await session.commit()
    if run.operation == "created" and run.status == "queued":
        LiteratureScoringScheduler.schedule(run.generation_id)
    return run


@router.post("/{result_id}/scoring/cancel", response_model=ScoringRunRead)
async def cancel_scoring_run(
    result_id: int, session: AsyncSession = Depends(get_session)
) -> ScoringRunRead:
    run = await LiteratureScoringService(session).cancel_run(result_id)
    await session.commit()
    LiteratureScoringScheduler.cancel(run.generation_id)
    return run


@router.get("/{result_id}/scoring/status", response_model=ScoringStatusRead)
async def get_scoring_status(
    result_id: int, session: AsyncSession = Depends(get_session)
) -> ScoringStatusRead:
    return await LiteratureScoringService(session).get_status(result_id)


@router.get(
    "/{result_id}/items/{pmid}/score-explanation", response_model=ScoreExplanationRead
)
async def get_score_explanation(
    result_id: int, pmid: str, session: AsyncSession = Depends(get_session)
) -> ScoreExplanationRead:
    return await LiteratureScoringService(session).get_explanation(result_id, pmid)
