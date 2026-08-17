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
    DocumentIndexResult,
    DocumentPage,
    DocumentRead,
    IndexStatus,
    ParseStatus,
)
from app.modules.document.service import DocumentService

router = APIRouter(prefix="/documents", tags=["文档"])


@router.get("", response_model=DocumentPage)
async def list_document(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    parse_status: ParseStatus | None = None,
    index_status: IndexStatus | None = None,
    query: str | None = Query(default=None, max_length=MAX_DOCUMENT_QUERY_LENGTH),
    research_ready: bool = False,
    previewable_only: bool = False,
    knowledge_source_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
) -> DocumentPage:
    service = DocumentService(session)
    return await service.list(
        offset,
        limit,
        parse_status,
        index_status,
        query,
        research_ready,
        previewable_only,
        knowledge_source_id,
    )


@router.post("/batch-index", response_model=BatchIndexResult)
async def batch_index_documents(
    request: BatchIndexRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchIndexResult:
    return await DocumentIndexService(session).batch_index(request.document_ids)


@router.get("/{id}", response_model=DocumentRead)
async def get_document(
    id: int,
    session: AsyncSession = Depends(get_session),
) -> DocumentRead:
    service = DocumentService(session)
    return DocumentRead.model_validate(await service.get(id))


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
        return DocumentRead.model_validate(await DocumentService(session).retry_parse(id))
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
        return DocumentRead.model_validate(await service.get(id))
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
