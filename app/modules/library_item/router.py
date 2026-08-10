"""HTTP boundary for local-library save and PDF-link operations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.library_item.open_fulltext_schema import (
    OpenFulltextAcquisitionRead,
    OpenFulltextRequest,
    OpenFulltextResult,
)
from app.modules.library_item.open_fulltext_service import OpenFulltextService
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


@router.post("/{id}/fulltext-retrievals", response_model=OpenFulltextResult)
async def acquire_open_access_fulltext(
    id: int,
    request: OpenFulltextRequest,
    session: AsyncSession = Depends(get_session),
) -> OpenFulltextResult:
    """仅在 PMC 官方身份、许可和 PDF 链接均可验证时才创建本地全文。"""
    return await OpenFulltextService(session).acquire(id, request.pmcid)


@router.get("/{id}/fulltext-retrievals", response_model=list[OpenFulltextAcquisitionRead])
async def list_open_fulltext_attempts(
    id: int, session: AsyncSession = Depends(get_session)
) -> list[OpenFulltextAcquisitionRead]:
    return await OpenFulltextService(session).list_attempts(id)


@router.get("", response_model=LibraryItemPage)
async def list_library_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fulltext_status: FulltextStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> LibraryItemPage:
    return await LibraryItemService(session).list(offset, limit, fulltext_status)
