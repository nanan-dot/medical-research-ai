"""evaluation — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.evaluation.service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["评测"])


@router.get("")
async def list_evaluation(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = EvaluationService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_evaluation(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = EvaluationService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_evaluation(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = EvaluationService(session)
    await service.delete(id)
