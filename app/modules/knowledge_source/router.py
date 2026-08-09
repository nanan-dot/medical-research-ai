"""Knowledge-source HTTP endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceRead,
    KnowledgeSourceSyncSummary,
    KnowledgeSourceUpdate,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService

router = APIRouter(prefix="/knowledge-sources", tags=["知识源"])


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
):
    service = KnowledgeSourceService(session)
    return await service.list(offset=offset, limit=limit)


@router.post(
    "", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_source(
    data: KnowledgeSourceCreate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRead:
    service = KnowledgeSourceService(session)
    return KnowledgeSourceRead.model_validate(await service.create(data))


@router.get("/{id}", response_model=KnowledgeSourceRead)
async def get_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = KnowledgeSourceService(session)
    return await service.get(id)


@router.patch("/{id}", response_model=KnowledgeSourceRead)
async def update_knowledge_source(
    id: int,
    data: KnowledgeSourceUpdate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRead:
    service = KnowledgeSourceService(session)
    return KnowledgeSourceRead.model_validate(await service.update(id, data))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = KnowledgeSourceService(session)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
