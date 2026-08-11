"""HTTP endpoints for the paper-research workspace."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.paper_research.schema import (
    IndexedDocumentPage,
    PaperResearchOverviewRead,
)
from app.modules.paper_research.service import PaperResearchService

router = APIRouter(prefix="/paper-research", tags=["论文研究"])
MAX_PAGE_SIZE = 100
DEFAULT_OVERVIEW_LIMIT = 10


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
    analysis_limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_OVERVIEW_LIMIT,
    pending_limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_OVERVIEW_LIMIT,
    conversation_limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_OVERVIEW_LIMIT,
) -> PaperResearchOverviewRead:
    return await PaperResearchService(session).overview(
        analysis_limit, pending_limit, conversation_limit
    )
