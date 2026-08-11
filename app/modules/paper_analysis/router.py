"""Single-paper analysis HTTP endpoints."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.paper_analysis.schema import (
    PaperAnalysisCorrection,
    PaperAnalysisCreate,
    PaperAnalysisRead,
)
from app.modules.paper_analysis.service import PaperAnalysisService

router = APIRouter(prefix="/paper-analysis", tags=["论文分析"])


@router.post("", response_model=PaperAnalysisRead)
async def create_analysis(
    request: PaperAnalysisCreate, session: AsyncSession = Depends(get_session)
):
    return await PaperAnalysisService(session).create(request.document_id)


@router.get("/latest", response_model=PaperAnalysisRead)
async def get_latest_analysis(
    document_id: int = Query(ge=1),
    session: AsyncSession = Depends(get_session),
) -> PaperAnalysisRead:
    return await PaperAnalysisService(session).latest_for_document(document_id)


@router.get("/{id}", response_model=PaperAnalysisRead)
async def get_analysis(id: int, session: AsyncSession = Depends(get_session)):
    return await PaperAnalysisService(session).get(id)


@router.post("/{id}/regenerate", response_model=PaperAnalysisRead)
async def regenerate_analysis(id: int, session: AsyncSession = Depends(get_session)):
    return await PaperAnalysisService(session).regenerate(id)


@router.patch("/{id}", response_model=PaperAnalysisRead)
async def correct_analysis(
    id: int,
    request: PaperAnalysisCorrection,
    session: AsyncSession = Depends(get_session),
):
    return await PaperAnalysisService(session).correct(id, request)


@router.get("/{id}/export")
async def export_analysis(id: int, session: AsyncSession = Depends(get_session)):
    content = await PaperAnalysisService(session).export_markdown(id)
    return Response(content, media_type="text/markdown; charset=utf-8")
