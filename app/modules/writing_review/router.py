"""HTTP endpoint for explicitly labelled simulated writing reviews."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.writing_review.schema import WritingReviewRead, WritingReviewRequest
from app.modules.writing_review.service import WritingReviewService

router = APIRouter(prefix="/writing-projects", tags=["writing-review"])


@router.post("/{project_id}/simulated-reviews", response_model=WritingReviewRead)
async def create_simulated_review(
    project_id: int,
    payload: WritingReviewRequest,
    session: AsyncSession = Depends(get_session),
) -> WritingReviewRead:
    return await WritingReviewService(session).review(project_id, payload)
