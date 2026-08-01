"""literature_search — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.literature_search.service import LiteratureSearchService

router = APIRouter(prefix="/literature-search", tags=["文献检索"])


@router.get("")
async def list_literature_search(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = LiteratureSearchService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_literature_search(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = LiteratureSearchService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_literature_search(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = LiteratureSearchService(session)
    await service.delete(id)
