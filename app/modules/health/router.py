"""health — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
async def list_health(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = HealthService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_health(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = HealthService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_health(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = HealthService(session)
    await service.delete(id)
