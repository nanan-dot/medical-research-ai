"""HTTP endpoints for feasibility scoring."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.feasibility.schema import FeasibilityRead, FeasibilityRequest, WeightPatch
from app.modules.feasibility.service import FeasibilityService

router = APIRouter(prefix="/research-directions", tags=["feasibility"])


@router.post("/{direction_id}/feasibility", response_model=FeasibilityRead)
async def create_feasibility_score(
    direction_id: int,
    payload: FeasibilityRequest,
    session: AsyncSession = Depends(get_session),
) -> FeasibilityRead:
    """Create an immutable initial score snapshot."""
    return await FeasibilityService(session).score(direction_id, payload)


@router.patch("/{direction_id}/feasibility/weights", response_model=FeasibilityRead)
async def patch_feasibility_weights(
    direction_id: int,
    payload: WeightPatch,
    session: AsyncSession = Depends(get_session),
) -> FeasibilityRead:
    """Create a new score version with prior user assessments inherited."""
    return await FeasibilityService(session).rescore_with_weights(
        direction_id,
        payload.weights,
    )


@router.get("/{direction_id}/feasibility/versions", response_model=list[FeasibilityRead])
async def list_feasibility_versions(
    direction_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[FeasibilityRead]:
    """Return all immutable score versions for a research direction."""
    return await FeasibilityService(session).versions(direction_id)
