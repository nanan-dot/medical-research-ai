"""writing — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.writing.service import WritingService

router = APIRouter(prefix="/writing", tags=["写作"])


@router.get("")
async def list_writing(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = WritingService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_writing(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = WritingService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_writing(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = WritingService(session)
    await service.delete(id)
