"""knowledge_source — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.knowledge_source.service import KnowledgeSourceService

router = APIRouter(prefix="/knowledge-source", tags=["知识源"])


@router.get("")
async def list_knowledge_source(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = KnowledgeSourceService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = KnowledgeSourceService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_knowledge_source(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = KnowledgeSourceService(session)
    await service.delete(id)
