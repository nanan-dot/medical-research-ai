"""conversation — HTTP 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.conversation.service import ConversationService

router = APIRouter(prefix="/conversation", tags=["会话"])


@router.get("")
async def list_conversation(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = ConversationService(session)
    return await service.list(offset=offset, limit=limit)


@router.get("/{id}")
async def get_conversation(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ConversationService(session)
    return await service.get(id)


@router.delete("/{id}", status_code=204)
async def delete_conversation(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ConversationService(session)
    await service.delete(id)
