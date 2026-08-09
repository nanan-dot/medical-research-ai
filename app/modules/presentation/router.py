"""Presentation outline HTTP endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.presentation.schema import (
    PresentationCreate,
    PresentationPatch,
    PresentationRead,
)
from app.modules.presentation.service import PresentationService

router = APIRouter(prefix="/presentations", tags=["presentations"])


@router.post("/outline", response_model=PresentationRead)
async def create_outline(
    payload: PresentationCreate, session: AsyncSession = Depends(get_session)
) -> PresentationRead:
    return await PresentationService(session).create(payload)


@router.get("/{presentation_id}", response_model=PresentationRead)
async def get_outline(
    presentation_id: int, session: AsyncSession = Depends(get_session)
) -> PresentationRead:
    return await PresentationService(session).get(presentation_id)


@router.patch("/{presentation_id}", response_model=PresentationRead)
async def patch_outline(
    presentation_id: int,
    payload: PresentationPatch,
    session: AsyncSession = Depends(get_session),
) -> PresentationRead:
    return await PresentationService(session).patch(presentation_id, payload)


@router.get("/{presentation_id}/export", response_class=PlainTextResponse)
async def export_outline(
    presentation_id: int, session: AsyncSession = Depends(get_session)
) -> str:
    return await PresentationService(session).export(presentation_id)
