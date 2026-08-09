"""候选研究方向的 HTTP 接口。"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.research_direction.schema import (
    ResearchDirectionGenerateRequest,
    ResearchDirectionPatch,
    ResearchDirectionRead,
)
from app.modules.research_direction.service import ResearchDirectionService

router = APIRouter(prefix="/research-directions", tags=["候选研究方向"])


@router.post("/generate", response_model=list[ResearchDirectionRead])
async def generate_research_directions(
    payload: ResearchDirectionGenerateRequest,
    session: AsyncSession = Depends(get_session),
) -> list[ResearchDirectionRead]:
    return await ResearchDirectionService(session).generate(payload)


@router.get("/{direction_id}", response_model=ResearchDirectionRead)
async def get_research_direction(
    direction_id: int, session: AsyncSession = Depends(get_session)
) -> ResearchDirectionRead:
    return await ResearchDirectionService(session).get(direction_id)


@router.get("/{direction_id}/details", response_model=ResearchDirectionRead)
async def get_research_direction_details(
    direction_id: int, session: AsyncSession = Depends(get_session)
) -> ResearchDirectionRead:
    """读取缓存；GET 的幂等语义禁止触发模型生成。"""
    return await ResearchDirectionService(session).get_details(direction_id)


@router.post("/{direction_id}/details", response_model=ResearchDirectionRead)
async def generate_research_direction_details(
    direction_id: int,
    model_config_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> ResearchDirectionRead:
    return await ResearchDirectionService(session).generate_details(
        direction_id, model_config_id
    )


@router.patch("/{direction_id}", response_model=ResearchDirectionRead)
async def patch_research_direction(
    direction_id: int,
    payload: ResearchDirectionPatch,
    session: AsyncSession = Depends(get_session),
) -> ResearchDirectionRead:
    return await ResearchDirectionService(session).patch(direction_id, payload)


@router.delete("/{direction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_direction(
    direction_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await ResearchDirectionService(session).delete(direction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
