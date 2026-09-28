"""HTTP routes for the unified research-resource library."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.modules.library.import_service import LibraryImportService
from app.modules.library.repository import LibraryQuery
from app.modules.library.schema import (
    DocumentOpenedRead,
    DocumentOpenedRequest,
    LibraryFacets,
    LibraryImportRead,
    LibraryItemPage,
    LibraryItemRead,
    LibrarySourceTree,
    LibraryStorageSummary,
    LibrarySummary,
)
from app.modules.library.service import LibraryService

router = APIRouter(prefix="/library", tags=["资料库"])


def _query(
    q: str | None, source_id: list[int] | None, source_type: list[str] | None,
    file_type: list[str] | None, health_status: list[str] | None,
    updated_from: datetime | None, updated_to: datetime | None, tree_node_id: str | None,
) -> LibraryQuery:
    tree = None
    if tree_node_id and tree_node_id.startswith("tree:"):
        _, source, path = tree_node_id.split(":", 2)
        tree = (int(source), path)
    return LibraryQuery(q=q.strip() if q else None, source_ids=tuple(source_id or ()), source_types=tuple(source_type or ()), file_types=tuple(file_type or ()), statuses=tuple(health_status or ()), updated_from=updated_from, updated_to=updated_to, tree_node=tree)


@router.get("/summary", response_model=LibrarySummary)
async def summary(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrarySummary:
    return await LibraryService(session).summary()


@router.get("/items", response_model=LibraryItemPage)
async def items(
    q: str | None = Query(default=None, max_length=200), source_id: list[int] | None = Query(default=None), source_type: list[str] | None = Query(default=None), file_type: list[str] | None = Query(default=None), health_status: list[str] | None = Query(default=None), updated_from: datetime | None = None, updated_to: datetime | None = None, tree_node_id: str | None = None,
    sort_by: str = Query(default="updated_at", pattern="^(updated_at|name|file_size|source_name|status|last_opened)$"), sort_order: str = Query(default="desc", pattern="^(asc|desc)$"), offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100), session: AsyncSession = Depends(get_session),
) -> LibraryItemPage:
    return await LibraryService(session).page(_query(q, source_id, source_type, file_type, health_status, updated_from, updated_to, tree_node_id), sort_by, sort_order, offset, limit)


@router.get("/facets", response_model=LibraryFacets)
async def facets(q: str | None = Query(default=None, max_length=200), source_id: list[int] | None = Query(default=None), source_type: list[str] | None = Query(default=None), file_type: list[str] | None = Query(default=None), health_status: list[str] | None = Query(default=None), session: AsyncSession = Depends(get_session)) -> LibraryFacets:
    return await LibraryService(session).facets(_query(q, source_id, source_type, file_type, health_status, None, None, None))


@router.get("/source-tree", response_model=LibrarySourceTree)
async def source_tree(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrarySourceTree:
    return await LibraryService(session).tree()


@router.get("/recent", response_model=LibraryItemPage)
async def recent(offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100), session: AsyncSession = Depends(get_session)) -> LibraryItemPage:
    return await LibraryService(session).recent(offset, limit)


@router.post("/imports", response_model=LibraryImportRead, status_code=status.HTTP_201_CREATED)
async def imports(files: list[UploadFile] = File(...), session: AsyncSession = Depends(get_session)) -> LibraryImportRead:
    return await LibraryImportService(session).import_files(files)


@router.get("/storage", response_model=LibraryStorageSummary)
async def storage(session: Annotated[AsyncSession, Depends(get_session)]) -> LibraryStorageSummary:
    return await LibraryService(session).storage(settings.LIBRARY_STORAGE_QUOTA_BYTES)


@router.post("/storage/refresh", response_model=LibraryStorageSummary)
async def refresh_storage(session: Annotated[AsyncSession, Depends(get_session)]) -> LibraryStorageSummary:
    return await LibraryService(session).storage(settings.LIBRARY_STORAGE_QUOTA_BYTES)


@router.get("/items/{document_id}", response_model=LibraryItemRead)
async def item(document_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> LibraryItemRead:
    return await LibraryService(session).item(document_id)


@router.post("/items/{document_id}/opened", response_model=DocumentOpenedRead)
async def opened(document_id: int, body: DocumentOpenedRequest | None = None, session: AsyncSession = Depends(get_session)) -> DocumentOpenedRead:
    payload = body or DocumentOpenedRequest()
    return await LibraryService(session).opened(document_id, payload.actor_id, payload.idempotency_key)


@router.post("/items/{document_id}/repair", status_code=status.HTTP_202_ACCEPTED)
async def repair(document_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, int]:
    task = await LibraryService(session).enqueue(document_id, "repair")
    return {"task_id": task.id}


@router.post("/items/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess(document_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, int]:
    task = await LibraryService(session).enqueue(document_id, "reindex")
    return {"task_id": task.id}
