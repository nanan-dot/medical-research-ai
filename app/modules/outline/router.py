from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.outline.schema import OutlineCreate, OutlineRead, OutlineUpdate
from app.modules.outline.service import OutlineService

router = APIRouter(prefix="/outlines", tags=["outlines"])


@router.post("/generate", response_model=OutlineRead)
async def generate(p: OutlineCreate, s: AsyncSession = Depends(get_session)) -> OutlineRead:
    return await OutlineService(s).create(p)


@router.get("/{id}", response_model=OutlineRead)
async def get(id: int, s: AsyncSession = Depends(get_session)) -> OutlineRead:
    return await OutlineService(s).get(id)


@router.patch("/{id}", response_model=OutlineRead)
async def update(id: int, p: OutlineUpdate, s: AsyncSession = Depends(get_session)) -> OutlineRead:
    return await OutlineService(s).update(id, p)


@router.post("/{id}/confirm", response_model=OutlineRead)
async def confirm(id: int, s: AsyncSession = Depends(get_session)) -> OutlineRead:
    return await OutlineService(s).confirm(id)
