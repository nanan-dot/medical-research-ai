"""HTTP boundary for local-library save and PDF-link operations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.library_item.schema import (
    FulltextStatus,
    LibraryItemPage,
    LibraryItemRead,
    LinkLocalPdfRequest,
    SaveLibraryItemRequest,
)
from app.modules.library_item.service import LibraryItemService

save_router = APIRouter(prefix="/literature-results", tags=["Local library"])
router = APIRouter(prefix="/library-items", tags=["Local library"])


@save_router.post("/{id}/save", response_model=LibraryItemRead)
async def save_result(
    id: int,
    request: SaveLibraryItemRequest,
    session: AsyncSession = Depends(get_session),
) -> LibraryItemRead:
    return await LibraryItemService(session).save_search_result(id, request.pmid)


@router.post("/{id}/link-local-pdf", response_model=LibraryItemRead)
async def link_local_pdf(
    id: int, request: LinkLocalPdfRequest, session: AsyncSession = Depends(get_session)
) -> LibraryItemRead:
    return await LibraryItemService(session).link_local_pdf(id, request.document_id)


@router.get("", response_model=LibraryItemPage)
async def list_library_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fulltext_status: FulltextStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> LibraryItemPage:
    return await LibraryItemService(session).list(offset, limit, fulltext_status)
