"""HTTP endpoints for the paper-research workspace."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.paper_research.center_schema import (
    ActivityPage,
    CenterRead,
    CurrentContextRead,
    CurrentContextStageUpdate,
    CurrentContextUpdate,
)
from app.modules.paper_research.center_service import CenterService
from app.modules.paper_research.schema import (
    IndexedDocumentPage,
    PaperResearchOverviewRead,
)
from app.modules.paper_research.service import PaperResearchService

router = APIRouter(prefix="/paper-research", tags=["论文研究"])
MAX_PAGE_SIZE = 100
DEFAULT_OVERVIEW_LIMIT = 10


@router.get("/center", response_model=CenterRead)
async def get_center(
    session: Annotated[AsyncSession, Depends(get_session)],
    continue_limit: Annotated[int, Query(ge=1, le=10)] = 3,
    activity_limit: Annotated[int, Query(ge=1, le=20)] = 5,
    recent_limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> CenterRead:
    return await CenterService(session).center(
        continue_limit, activity_limit, recent_limit
    )


@router.get("/current-context", response_model=CurrentContextRead | None)
async def get_current_context(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentContextRead | None:
    return await CenterService(session).current_context()


@router.put("/current-context", response_model=CurrentContextRead)
async def set_current_context(
    payload: CurrentContextUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentContextRead:
    return await CenterService(session).set_context(payload)


@router.patch("/current-context/stage", response_model=CurrentContextRead)
async def update_current_context_stage(
    payload: CurrentContextStageUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentContextRead:
    return await CenterService(session).update_stage(payload)


@router.get("/activities", response_model=ActivityPage)
async def list_center_activities(
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> ActivityPage:
    return await CenterService(session).activity_page(cursor, limit)


@router.get("/indexed-documents", response_model=IndexedDocumentPage)
async def list_indexed_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> IndexedDocumentPage:
    return await PaperResearchService(session).indexed_documents(q, offset, limit)


@router.get("/overview", response_model=PaperResearchOverviewRead)
async def get_overview(
    session: Annotated[AsyncSession, Depends(get_session)],
    analysis_limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE)
    ] = DEFAULT_OVERVIEW_LIMIT,
    pending_limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE)
    ] = DEFAULT_OVERVIEW_LIMIT,
    conversation_limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE)
    ] = DEFAULT_OVERVIEW_LIMIT,
) -> PaperResearchOverviewRead:
    return await PaperResearchService(session).overview(
        analysis_limit, pending_limit, conversation_limit
    )
