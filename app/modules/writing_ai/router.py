"""HTTP endpoints for AI writing suggestions, which remain unconfirmed by default."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.writing_ai.schema import (
    WritingGenerationRequest,
    WritingSuggestionRead,
)
from app.modules.writing_ai.service import WritingAiService

router = APIRouter(prefix="/writing-projects", tags=["writing-ai"])


@router.post("/{project_id}/ai-suggestions", response_model=WritingSuggestionRead)
async def generate_suggestion(
    project_id: int,
    payload: WritingGenerationRequest,
    session: AsyncSession = Depends(get_session),
) -> WritingSuggestionRead:
    return await WritingAiService(session).generate(project_id, payload)


@router.post(
    "/{project_id}/ai-suggestions/{suggestion_id}/confirm",
    response_model=WritingSuggestionRead,
)
async def confirm_suggestion(
    project_id: int, suggestion_id: int, session: AsyncSession = Depends(get_session)
) -> WritingSuggestionRead:
    return await WritingAiService(session).confirm(project_id, suggestion_id)
