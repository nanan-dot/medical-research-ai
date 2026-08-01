"""feedback — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.feedback.service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["反馈"])


@router.get("")
async def list_feedback(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = FeedbackService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_feedback(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = FeedbackService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_feedback(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = FeedbackService(session)
    await service.delete(id)
