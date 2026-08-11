"""Read-only publish-readiness endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.writing_coverage.schema import PublishReadinessRead
from app.modules.writing_coverage.service import WritingCoverageService

router = APIRouter(prefix="/writing-projects", tags=["writing-coverage"])


@router.get("/{project_id}/publish-readiness", response_model=PublishReadinessRead)
async def check_publish_readiness(
    project_id: int, session: AsyncSession = Depends(get_session)
) -> PublishReadinessRead:
    return await WritingCoverageService(session).check(project_id)
