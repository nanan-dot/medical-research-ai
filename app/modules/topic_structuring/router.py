"""HTTP entry points for topic structuring."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.topic_structuring.schema import (
    TopicStructuringParseRequest,
    TopicStructuringPatchRequest,
    TopicStructuringRead,
)
from app.modules.topic_structuring.service import TopicStructuringService

router = APIRouter(prefix="/topic-structuring", tags=["研究主题结构化"])


@router.post("/parse", response_model=TopicStructuringRead)
async def parse_topic(
    payload: TopicStructuringParseRequest,
    session: AsyncSession = Depends(get_session),
) -> TopicStructuringRead:
    return await TopicStructuringService(session).parse(payload)


@router.get("/{structuring_id}", response_model=TopicStructuringRead)
async def get_topic_structuring(
    structuring_id: int, session: AsyncSession = Depends(get_session)
) -> TopicStructuringRead:
    return await TopicStructuringService(session).get(structuring_id)


@router.patch("/{structuring_id}", response_model=TopicStructuringRead)
async def patch_topic_structuring(
    structuring_id: int,
    payload: TopicStructuringPatchRequest,
    session: AsyncSession = Depends(get_session),
) -> TopicStructuringRead:
    return await TopicStructuringService(session).patch(structuring_id, payload)
