"""research_direction — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.research_direction.service import ResearchDirectionService

router = APIRouter(prefix="/research-direction", tags=["研究方向"])


@router.get("")
async def list_research_direction(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = ResearchDirectionService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_research_direction(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ResearchDirectionService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_research_direction(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ResearchDirectionService(session)
    await service.delete(id)
