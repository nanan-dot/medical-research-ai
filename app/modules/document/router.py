"""document — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.document.service import DocumentService

router = APIRouter(prefix="/document", tags=["文档"])


@router.get("")
async def list_document(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = DocumentService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_document(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = DocumentService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_document(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = DocumentService(session)
    await service.delete(id)
