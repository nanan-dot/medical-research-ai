from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.feasibility.schema import FeasibilityRead, FeasibilityRequest
from app.modules.feasibility.service import FeasibilityService
router=APIRouter(prefix="/research-directions",tags=["可行性评分"])
@router.post("/{direction_id}/feasibility",response_model=FeasibilityRead)
async def score(direction_id:int,payload:FeasibilityRequest,session:AsyncSession=Depends(get_session))->FeasibilityRead:return await FeasibilityService(session).score(direction_id,payload)
@router.patch("/{direction_id}/feasibility/weights",response_model=FeasibilityRead)
async def weights(direction_id:int,payload:FeasibilityRequest,session:AsyncSession=Depends(get_session))->FeasibilityRead:return await FeasibilityService(session).score(direction_id,payload)
@router.get("/{direction_id}/feasibility/versions",response_model=list[FeasibilityRead])
async def versions(direction_id:int,session:AsyncSession=Depends(get_session))->list[FeasibilityRead]:return await FeasibilityService(session).versions(direction_id)
