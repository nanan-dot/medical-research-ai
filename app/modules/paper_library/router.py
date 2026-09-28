"""论文库 FastAPI 路由边界。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.paper_library.query import (
    AnalysisStatus,
    PaperLibraryFilters,
    PaperLibraryView,
    PaperSort,
)
from app.modules.paper_library.schema import (
    ActivityRead,
    PaperAddRequest,
    PaperAddResult,
    PaperItemPage,
    PaperItemRead,
    PaperLibraryFacets,
    PaperLibrarySummary,
    PaperOverviewRead,
    PaperTagsUpdate,
    ReadingStateRead,
    ReadingStateUpdate,
    ReadingStatus,
    ResearchRelationRead,
    ResearchRelationUpdate,
    ResearchRole,
)
from app.modules.paper_library.service import PaperLibraryService

router = APIRouter(prefix="/paper-library", tags=["paper-library"])


@router.get("/summary", response_model=PaperLibrarySummary)
async def summary(session: AsyncSession = Depends(get_session)) -> PaperLibrarySummary:
    return await PaperLibraryService(session).summary()


@router.get("/items", response_model=PaperItemPage)
async def list_items(
    view: PaperLibraryView = PaperLibraryView.ALL,
    query: str = Query(default="", max_length=300),
    reading_status: Annotated[list[ReadingStatus] | None, Query()] = None,
    analysis_status: Annotated[list[AnalysisStatus] | None, Query()] = None,
    paper_type: Annotated[list[str] | None, Query()] = None,
    research_role: Annotated[list[ResearchRole] | None, Query()] = None,
    research_id: Annotated[list[int] | None, Query()] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort: PaperSort = PaperSort.RECENT_ACTIVITY,
    session: AsyncSession = Depends(get_session),
) -> PaperItemPage:
    filters = PaperLibraryFilters(
        reading_status=[status.value for status in reading_status or []],
        analysis_status=[status.value for status in analysis_status or []],
        paper_types=paper_type or [],
        research_roles=[role.value for role in research_role or []],
        research_ids=research_id or [],
        tags=tag or [],
        query=query,
    )
    return await PaperLibraryService(session).list_items(
        view=view, filters=filters, offset=offset, limit=limit, sort=sort
    )


@router.get("/facets", response_model=PaperLibraryFacets)
async def facets(
    view: PaperLibraryView = PaperLibraryView.ALL,
    query: str = Query(default="", max_length=300),
    reading_status: Annotated[list[ReadingStatus] | None, Query()] = None,
    analysis_status: Annotated[list[AnalysisStatus] | None, Query()] = None,
    paper_type: Annotated[list[str] | None, Query()] = None,
    research_role: Annotated[list[ResearchRole] | None, Query()] = None,
    research_id: Annotated[list[int] | None, Query()] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
) -> PaperLibraryFacets:
    filters = PaperLibraryFilters(
        reading_status=[status.value for status in reading_status or []],
        analysis_status=[status.value for status in analysis_status or []],
        paper_types=paper_type or [],
        research_roles=[role.value for role in research_role or []],
        research_ids=research_id or [],
        tags=tag or [],
        query=query,
    )
    return await PaperLibraryService(session).facets(view, filters)


@router.post("/items", response_model=PaperAddResult, status_code=201)
async def add_item(
    payload: PaperAddRequest, session: AsyncSession = Depends(get_session)
) -> PaperAddResult:
    return await PaperLibraryService(session).add(payload)


@router.get("/items/{item_id}/overview", response_model=PaperOverviewRead)
async def overview(
    item_id: int, session: AsyncSession = Depends(get_session)
) -> PaperOverviewRead:
    return await PaperLibraryService(session).overview(item_id)


@router.post("/items/{item_id}/metadata/refresh", response_model=PaperItemRead)
async def refresh_metadata(
    item_id: int, session: AsyncSession = Depends(get_session)
) -> PaperItemRead:
    return await PaperLibraryService(session).refresh_metadata(item_id)


@router.patch("/items/{item_id}/reading-state", response_model=ReadingStateRead)
async def update_reading_state(
    item_id: int,
    payload: ReadingStateUpdate,
    session: AsyncSession = Depends(get_session),
) -> ReadingStateRead:
    return await PaperLibraryService(session).update_reading_state(item_id, payload)


@router.put("/items/{item_id}/tags", response_model=list[str])
async def update_tags(
    item_id: int, payload: PaperTagsUpdate, session: AsyncSession = Depends(get_session)
) -> list[str]:
    return await PaperLibraryService(session).update_tags(item_id, payload.tags)


@router.get("/items/{item_id}/activities", response_model=list[ActivityRead])
async def activities(
    item_id: int, session: AsyncSession = Depends(get_session)
) -> list[ActivityRead]:
    return await PaperLibraryService(session).activities_for(item_id)


@router.put(
    "/items/{item_id}/research-relations/{research_id}",
    response_model=ResearchRelationRead,
)
async def upsert_relation(
    item_id: int,
    research_id: int,
    payload: ResearchRelationUpdate,
    session: AsyncSession = Depends(get_session),
) -> ResearchRelationRead:
    return await PaperLibraryService(session).upsert_relation(
        item_id, research_id, payload
    )


@router.delete("/items/{item_id}/research-relations/{research_id}", status_code=204)
async def delete_relation(
    item_id: int,
    research_id: int,
    expected_version: int = Query(ge=1),
    session: AsyncSession = Depends(get_session),
) -> None:
    await PaperLibraryService(session).delete_relation(
        item_id, research_id, expected_version
    )
