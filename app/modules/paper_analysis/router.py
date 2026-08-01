"""paper_analysis — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.paper_analysis.service import PaperAnalysisService

router = APIRouter(prefix="/paper-analysis", tags=["论文分析"])


@router.get("")
async def list_paper_analysis(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = PaperAnalysisService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_paper_analysis(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = PaperAnalysisService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_paper_analysis(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = PaperAnalysisService(session)
    await service.delete(id)
