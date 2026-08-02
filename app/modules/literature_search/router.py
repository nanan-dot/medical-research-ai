"""Literature-search endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.literature_search.schema import ParseQueryRequest, ParseQueryResponse
from app.modules.literature_search.service import LiteratureSearchService

router = APIRouter(prefix="/literature-search", tags=["Literature search"])


@router.get("")
async def list_literature_search(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    return await LiteratureSearchService(session).list_records(offset=offset, limit=limit)


@router.post("/parse-query", response_model=ParseQueryResponse)
async def parse_query(
    request: ParseQueryRequest,
    session: AsyncSession = Depends(get_session),
) -> ParseQueryResponse:
    return await LiteratureSearchService(session).parse_query(request.raw_topic)


@router.get("/{id}")
async def get_literature_search(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    return await LiteratureSearchService(session).get(id)


@router.delete("/{id}", status_code=204)
async def delete_literature_search(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    await LiteratureSearchService(session).delete(id)
