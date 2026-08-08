"""AI 使用披露 HTTP 接口。"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ai_disclosure.schema import AIUsageEventCreate, AIUsageEventRead, DisclosureDraftRead
from app.modules.ai_disclosure.service import AIDisclosureService

router = APIRouter(prefix="/ai-disclosure", tags=["ai-disclosure"])


@router.post("/events", response_model=AIUsageEventRead)
async def add_event(
    project_id: int,
    payload: AIUsageEventCreate,
    session: AsyncSession = Depends(get_session),
) -> AIUsageEventRead:
    return await AIDisclosureService(session).add_event(project_id, payload)


@router.get("/projects/{project_id}/events", response_model=list[AIUsageEventRead])
async def list_events(project_id: int, session: AsyncSession = Depends(get_session)) -> list[AIUsageEventRead]:
    return await AIDisclosureService(session).list_events(project_id)


@router.get("/projects/{project_id}/draft", response_model=DisclosureDraftRead)
async def get_project_draft(project_id: int, session: AsyncSession = Depends(get_session)) -> DisclosureDraftRead:
    return await AIDisclosureService(session).get_or_create_draft(project_id)


@router.patch("/drafts/{draft_id}", response_model=DisclosureDraftRead)
async def update_draft(
    draft_id: int,
    content: str,
    session: AsyncSession = Depends(get_session),
) -> DisclosureDraftRead:
    return await AIDisclosureService(session).update_draft(draft_id, content)


@router.get("/drafts/{draft_id}/export", response_class=PlainTextResponse)
async def export_draft(draft_id: int, session: AsyncSession = Depends(get_session)) -> str:
    draft = await AIDisclosureService(session).get_draft(draft_id)
    return draft.content
