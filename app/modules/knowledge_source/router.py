"""Knowledge-source HTTP endpoints."""

import asyncio

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.knowledge_source.browse_service import (
    select_authorized_directory,
)
from app.modules.knowledge_source.import_service import (
    KnowledgeSourceDocumentImportService,
)
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceDirectoryBrowseRead,
    KnowledgeSourceDocumentImportRead,
    KnowledgeSourceRead,
    KnowledgeSourceStats,
    KnowledgeSourceSyncSummary,
    KnowledgeSourceUpdate,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService

router = APIRouter(prefix="/knowledge-sources", tags=["知识源"])


@router.post(
    "/browse-directory",
    response_model=KnowledgeSourceDirectoryBrowseRead,
)
async def browse_knowledge_source_directory() -> KnowledgeSourceDirectoryBrowseRead:
    """在线程中打开阻塞式原生目录选择器，避免阻塞 API 事件循环。"""
    selected_path = await asyncio.to_thread(select_authorized_directory)
    return KnowledgeSourceDirectoryBrowseRead(path=selected_path)


@router.post(
    "/import-document",
    response_model=KnowledgeSourceDocumentImportRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_document_to_knowledge_source(
    file: UploadFile = File(...),
    knowledge_source_id: int | None = Form(default=None),
    new_source_name: str | None = Form(default=None),
    relative_directory: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceDocumentImportRead:
    return await KnowledgeSourceDocumentImportService(session).import_document(
        file=file,
        knowledge_source_id=knowledge_source_id,
        new_source_name=new_source_name,
        relative_directory=relative_directory,
    )


@router.post("/{id}/sync", response_model=KnowledgeSourceSyncSummary)
async def sync_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceSyncSummary:
    return await KnowledgeSourceSyncService(session).sync(id)


@router.get("/{id}/sync-status", response_model=KnowledgeSourceSyncSummary)
async def get_knowledge_source_sync_status(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceSyncSummary:
    return await KnowledgeSourceSyncService(session).status(id)


@router.get("", response_model=list[KnowledgeSourceRead])
async def list_knowledge_sources(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeSourceRead]:
    service = KnowledgeSourceService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}/stats", response_model=KnowledgeSourceStats)
async def get_knowledge_source_stats(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceStats:
    return await KnowledgeSourceService(session).stats(id)


@router.post(
    "", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_source(
    data: KnowledgeSourceCreate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRead:
    service = KnowledgeSourceService(session)
    entity = await service.create(data)
    return await service.read(entity.id)


@router.get("/{id}", response_model=KnowledgeSourceRead)
async def get_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRead:
    return await KnowledgeSourceService(session).read(id)


@router.patch("/{id}", response_model=KnowledgeSourceRead)
async def update_knowledge_source(
    id: int,
    data: KnowledgeSourceUpdate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRead:
    service = KnowledgeSourceService(session)
    entity = await service.update(id, data)
    return await service.read(entity.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = KnowledgeSourceService(session)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
