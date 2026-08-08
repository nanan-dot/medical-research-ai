"""HTTP API for advisor confirmation workflow."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.advisor_workflow.schema import (
    AdvisorNoteCreate,
    AdvisorReviewRead,
    DirectionVersionRead,
    MockReviewRequest,
)
from app.modules.advisor_workflow.service import AdvisorWorkflowService

router = APIRouter(prefix="/research-directions", tags=["advisor-workflow"])


@router.post("/{direction_id}/advisor-notes", response_model=AdvisorReviewRead)
async def create_advisor_note(
    direction_id: int, payload: AdvisorNoteCreate, session: AsyncSession = Depends(get_session)
) -> AdvisorReviewRead:
    return await AdvisorWorkflowService(session).record_note(direction_id, payload)


@router.get("/{direction_id}/advisor-notes", response_model=list[AdvisorReviewRead])
async def list_advisor_notes(
    direction_id: int, session: AsyncSession = Depends(get_session)
) -> list[AdvisorReviewRead]:
    return await AdvisorWorkflowService(session).list_notes(direction_id)


@router.post("/{direction_id}/mock-review", response_model=AdvisorReviewRead)
async def create_mock_review(
    direction_id: int,
    payload: MockReviewRequest,
    session: AsyncSession = Depends(get_session),
) -> AdvisorReviewRead:
    return await AdvisorWorkflowService(session).mock_review(direction_id, payload)


@router.post("/{direction_id}/revise", response_model=DirectionVersionRead)
async def revise_direction(
    direction_id: int, review_id: int, session: AsyncSession = Depends(get_session)
) -> DirectionVersionRead:
    return await AdvisorWorkflowService(session).revise(direction_id, review_id)


@router.get("/{direction_id}/versions", response_model=list[DirectionVersionRead])
async def list_direction_versions(
    direction_id: int, session: AsyncSession = Depends(get_session)
) -> list[DirectionVersionRead]:
    return await AdvisorWorkflowService(session).versions(direction_id)


@router.post("/{direction_id}/export-report", response_class=PlainTextResponse)
async def export_report(direction_id: int, session: AsyncSession = Depends(get_session)) -> str:
    return await AdvisorWorkflowService(session).export_markdown(direction_id)
