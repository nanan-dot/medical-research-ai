"""研究条件 HTTP 接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.research_conditions.schema import (
    ResearchConditionsCreate,
    ResearchConditionsPatch,
    ResearchConditionsRead,
)
from app.modules.research_conditions.service import ResearchConditionsService

router = APIRouter(prefix="/research-conditions", tags=["研究条件"])


@router.post("", response_model=ResearchConditionsRead)
async def create_research_conditions(
    payload: ResearchConditionsCreate,
    session: AsyncSession = Depends(get_session),
) -> ResearchConditionsRead:
    return await ResearchConditionsService(session).create(payload)


@router.get("/{conditions_id}", response_model=ResearchConditionsRead)
async def get_research_conditions(
    conditions_id: int,
    session: AsyncSession = Depends(get_session),
) -> ResearchConditionsRead:
    return await ResearchConditionsService(session).get(conditions_id)


@router.patch("/{conditions_id}", response_model=ResearchConditionsRead)
async def patch_research_conditions(
    conditions_id: int,
    payload: ResearchConditionsPatch,
    session: AsyncSession = Depends(get_session),
) -> ResearchConditionsRead:
    return await ResearchConditionsService(session).patch(conditions_id, payload)
