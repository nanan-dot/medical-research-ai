"""Knowledge-source HTTP endpoints."""

import asyncio

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.modules.knowledge_source.browse_service import (
    select_authorized_directory,
)
from app.modules.knowledge_source.directory_open_service import (
    KnowledgeSourceDirectoryOpenService,
)
from app.modules.knowledge_source.import_service import (
    KnowledgeSourceDocumentImportService,
)
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.schema import (
    KnowledgeBaseSummary,
    KnowledgeSourceCreate,
    KnowledgeSourceDirectoryBrowseRead,
    KnowledgeSourceDocumentImportRead,
    KnowledgeSourceHealthStatus,
    KnowledgeSourcePage,
    KnowledgeSourceRead,
    KnowledgeSourceResearchContextRead,
    KnowledgeSourceSortBy,
    KnowledgeSourceStats,
    KnowledgeSourceSyncAccepted,
    KnowledgeSourceSyncSummary,
    KnowledgeSourceUpdate,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService
from app.modules.knowledge_source.sync_task_service import (
    KnowledgeSourceSyncTaskService,
)
from app.modules.library.schema import ZoteroSourceCreate
from app.modules.library.zotero import ZoteroAdapter
from app.modules.library.zotero_service import ZoteroSourceService
from app.modules.library.zotero_task_service import ZoteroSyncTaskService

router = APIRouter(prefix="/knowledge-sources", tags=["知识源"])

@router.post("/zotero/connection-test")
async def zotero_connection_test(
    library_type: str = Query(default="users", pattern="^(users|groups)$"),
    library_id: str = Query(default=""),
) -> dict[str, str | None]:
    """Fail structurally when the optional official integration is not configured."""
    if not settings.ZOTERO_API_KEY:
        from app.modules.library.zotero import ZoteroNotConfiguredError
        raise ZoteroNotConfiguredError("Zotero is not configured")
    if not library_id:
        return {"status": "configured", "version": None}
    async with httpx.AsyncClient() as client:
        version = await ZoteroAdapter(
            settings.ZOTERO_API_KEY, library_type, library_id,
            client=client, base_url=settings.ZOTERO_API_BASE_URL,
            max_retries=settings.ZOTERO_MAX_RETRIES,
            timeout_seconds=settings.ZOTERO_TIMEOUT_SECONDS,
        ).connection_test()
    return {"status": "connected", "version": version}


@router.post("/zotero", status_code=status.HTTP_201_CREATED)
async def create_zotero_source(
    payload: ZoteroSourceCreate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | str]:
    library = await ZoteroSourceService(session).create(payload)
    return {
        "knowledge_source_id": library.knowledge_source_id,
        "zotero_library_id": library.id,
        "status": "configured" if settings.ZOTERO_API_KEY else "not_configured",
    }


@router.delete("/zotero/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zotero_source(
    source_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await ZoteroSourceService(session).delete(source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=KnowledgeBaseSummary)
async def get_knowledge_base_summary(
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBaseSummary:
    """Return global, non-paginated source and document availability counts."""
    return await KnowledgeSourceService(session).summary()


@router.get("/page", response_model=KnowledgeSourcePage)
async def page_knowledge_sources(
    q: str | None = Query(default=None, max_length=200),
    source_type: str | None = Query(
        default=None, pattern="^(local_folder|obsidian_vault|zotero_library)$"
    ),
    health_status: KnowledgeSourceHealthStatus | None = None,
    enabled: bool | None = None,
    auto_sync: bool | None = None,
    is_pinned: bool | None = None,
    research_context_id: int | None = Query(default=None, ge=1),
    sort_by: KnowledgeSourceSortBy = KnowledgeSourceSortBy.PINNED,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourcePage:
    page = await KnowledgeSourceService(session).page(
        q,
        source_type,
        health_status.value if health_status else None,
        enabled,
        auto_sync,
        is_pinned,
        research_context_id,
        sort_by.value,
        sort_order,
        offset,
        limit,
    )
    return page


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


@router.post(
    "/{id}/sync",
    response_model=KnowledgeSourceSyncAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceSyncAccepted:
    source = await KnowledgeSourceService(session).get(id)
    task = (
        await ZoteroSyncTaskService(session).enqueue(id)
        if source.source_type == "zotero_library"
        else await KnowledgeSourceSyncTaskService(session).enqueue(id)
    )
    return KnowledgeSourceSyncAccepted(
        task_id=task.id,
        knowledge_source_id=id,
        status=task.status,
        status_url=f"/api/v1/tasks/{task.id}",
    )


@router.get("/{id}/sync-status", response_model=KnowledgeSourceSyncSummary)
async def get_knowledge_source_sync_status(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceSyncSummary:
    return await KnowledgeSourceSyncService(session).status(id)


@router.post("/{id}/opened", status_code=status.HTTP_204_NO_CONTENT)
async def record_knowledge_source_opened(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """记录用户从知识库进入来源内容的真实访问事件。"""
    await KnowledgeSourceService(session).record_opened(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/open-directory", status_code=status.HTTP_204_NO_CONTENT)
async def open_knowledge_source_directory(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """在明确启用的本机桌面部署中打开已经授权的来源目录。"""
    service = KnowledgeSourceDirectoryOpenService(
        KnowledgeSourceRepository(session), settings
    )
    await service.open_source_directory(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id}/research-contexts",
    response_model=list[KnowledgeSourceResearchContextRead],
)
async def list_source_research_contexts(
    id: int, session: AsyncSession = Depends(get_session)
) -> list[KnowledgeSourceResearchContextRead]:
    return await KnowledgeSourceService(session).research_contexts(id)


@router.put("/{id}/research-contexts/{context_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_source_research_context(
    id: int, context_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await KnowledgeSourceService(session).add_research_context(id, context_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{id}/research-contexts/{context_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_source_research_context(
    id: int, context_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await KnowledgeSourceService(session).remove_research_context(id, context_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
