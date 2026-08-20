"""Document status and task-management endpoints."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.core.database import get_session
from app.modules.document.index_service import DocumentIndexService
from app.modules.document.parsers.schemas import ParsedContentSummary
from app.modules.document.schema import (
    MAX_DOCUMENT_QUERY_LENGTH,
    BatchIndexRequest,
    BatchIndexResult,
    ContentSearchPage,
    DocumentBatchTaskItem,
    DocumentBatchTaskRead,
    DocumentBatchTaskRequest,
    DocumentFileType,
    DocumentHealthStatus,
    DocumentIndexResult,
    DocumentMode,
    DocumentPage,
    DocumentRead,
    DocumentRepairRead,
    DocumentSortBy,
    DocumentStatistics,
    IndexStatus,
    ParseStatus,
)
from app.modules.document.service import DocumentService
from app.modules.document.task_service import DocumentTaskService

router = APIRouter(prefix="/documents", tags=["文档"])


@router.get("", response_model=DocumentPage | ContentSearchPage)
async def list_document(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    mode: DocumentMode = DocumentMode.DOCUMENT,
    parse_status: ParseStatus | None = None,
    index_status: IndexStatus | None = None,
    query: str | None = Query(default=None, max_length=MAX_DOCUMENT_QUERY_LENGTH),
    research_ready: bool = False,
    previewable_only: bool = False,
    knowledge_source_id: int | None = Query(default=None, ge=1),
    needs_attention: bool = False,
    file_type: DocumentFileType | None = None,
    health_status: DocumentHealthStatus | None = None,
    sort_by: DocumentSortBy = DocumentSortBy.UPDATED_AT,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
) -> DocumentPage | ContentSearchPage:
    service = DocumentService(session)
    if mode == DocumentMode.CONTENT:
        return await service.search_content(
            query or "",
            offset,
            limit,
            knowledge_source_id,
            file_type,
            health_status,
            sort_by.value,
            sort_order,
        )
    return await service.list(
        offset,
        limit,
        parse_status,
        index_status,
        query,
        research_ready,
        previewable_only,
        knowledge_source_id,
        needs_attention,
        file_type,
        health_status,
        sort_by.value,
        sort_order,
    )


@router.post("/batch-index", response_model=BatchIndexResult)
async def batch_index_documents(
    request: BatchIndexRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchIndexResult:
    return await DocumentIndexService(session).batch_index(request.document_ids)


@router.get("/statistics", response_model=DocumentStatistics)
async def get_document_statistics(
    session: AsyncSession = Depends(get_session),
) -> DocumentStatistics:
    return await DocumentService(session).statistics()


@router.post("/{id}/repair", response_model=DocumentRepairRead)
async def repair_document(
    id: int, session: AsyncSession = Depends(get_session)
) -> DocumentRepairRead:
    document = await DocumentService(session).get(id)
    task = await DocumentTaskService(session).enqueue(id, "repair")
    return DocumentRepairRead(
        document_id=document.id,
        action="repair",
        task_id=task.id,
        status="queued",
        health_status=DocumentHealthStatus.PROCESSING,
    )


async def _enqueue_batch(request: DocumentBatchTaskRequest, operation: str, session: AsyncSession) -> DocumentBatchTaskRead:
    operation_id, tasks = await DocumentTaskService(session).enqueue_many(request.document_ids, operation)
    items: list[DocumentBatchTaskItem] = []
    for task in tasks:
        if task.source_id is None:
            raise RuntimeError("Document batch task is missing its document identifier")
        items.append(
            DocumentBatchTaskItem(
                document_id=task.source_id,
                task_id=task.id,
                accepted=True,
            )
        )
    return DocumentBatchTaskRead(
        operation_id=operation_id,
        accepted=len(items),
        items=items,
    )


@router.post("/batch-repair", response_model=DocumentBatchTaskRead)
async def batch_repair(request: DocumentBatchTaskRequest, session: AsyncSession = Depends(get_session)) -> DocumentBatchTaskRead:
    return await _enqueue_batch(request, "repair", session)


@router.post("/batch-reparse", response_model=DocumentBatchTaskRead)
async def batch_reparse(request: DocumentBatchTaskRequest, session: AsyncSession = Depends(get_session)) -> DocumentBatchTaskRead:
    return await _enqueue_batch(request, "reparse", session)


@router.post("/batch-reindex", response_model=DocumentBatchTaskRead)
async def batch_reindex(request: DocumentBatchTaskRequest, session: AsyncSession = Depends(get_session)) -> DocumentBatchTaskRead:
    return await _enqueue_batch(request, "reindex", session)


@router.get("/{id}", response_model=DocumentRead)
async def get_document(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    service = DocumentService(session)
    return service._to_read(await service.get(id))


@router.post("/{id}/parse", response_model=ParsedContentSummary)
async def parse_document(
    id: int, session: AsyncSession = Depends(get_session)
) -> ParsedContentSummary:
    return await DocumentService(session).parse(id)


@router.get("/{id}/content-summary", response_model=ParsedContentSummary)
async def get_document_content_summary(
    id: int, session: AsyncSession = Depends(get_session)
) -> ParsedContentSummary:
    return await DocumentService(session).content_summary(id)


@router.post("/{id}/retry-parse", response_model=DocumentRead)
async def retry_document_parse(
    id: int, session: AsyncSession = Depends(get_session)
) -> DocumentRead:
    try:
        service = DocumentService(session)
        return service._to_read(await service.retry_parse(id))
    except ConflictError:
        await session.commit()
        raise


@router.post("/{id}/retry-index", response_model=DocumentRead)
async def retry_document_index(
    id: int, session: AsyncSession = Depends(get_session)
) -> DocumentRead:
    service = DocumentService(session)
    try:
        await service.retry_index(id)
        await DocumentIndexService(session).index(id)
        return service._to_read(await service.get(id))
    except ConflictError:
        await session.commit()
        raise


@router.post("/{id}/index", response_model=DocumentIndexResult)
async def index_document(
    id: int, session: AsyncSession = Depends(get_session)
) -> DocumentIndexResult:
    try:
        return await DocumentIndexService(session).index(id)
    except ConflictError:
        await session.commit()
        raise


@router.delete("/{id}/index", response_model=DocumentIndexResult)
async def delete_document_index(
    id: int, session: AsyncSession = Depends(get_session)
) -> DocumentIndexResult:
    return await DocumentIndexService(session).delete_index(id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = DocumentService(session)
    await service.delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
