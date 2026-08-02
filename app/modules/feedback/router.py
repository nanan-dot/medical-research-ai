from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.feedback.schema import FeedbackCreate, FeedbackRead
from app.modules.feedback.service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["反馈"])


@router.post("", response_model=FeedbackRead)
async def create_feedback(request: FeedbackCreate, session: AsyncSession = Depends(get_session)):
    return await FeedbackService(session).create(request)


@router.get("", response_model=list[FeedbackRead])
async def list_feedback(session: AsyncSession = Depends(get_session)):
    return await FeedbackService(session).list()


@router.get("/export")
async def export_feedback(session: AsyncSession = Depends(get_session)):
    return Response(
        await FeedbackService(session).anonymous_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anonymous-feedback.csv"},
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(id: int, session: AsyncSession = Depends(get_session)):
    await FeedbackService(session).delete(id)
