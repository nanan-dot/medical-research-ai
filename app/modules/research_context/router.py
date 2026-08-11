"""HTTP endpoints for persistent research contexts."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.research_context.schema import (
    ResearchContextCreate,
    ResearchContextDocumentAdd,
    ResearchContextRead,
    ResearchContextUpdate,
)
from app.modules.research_context.service import ResearchContextService

router = APIRouter(prefix="/research-contexts", tags=["research-contexts"])


@router.post("", response_model=ResearchContextRead, status_code=201)
async def create_context(
    payload: ResearchContextCreate, session: AsyncSession = Depends(get_session)
) -> ResearchContextRead:
    return await ResearchContextService(session).create(payload)


@router.get("", response_model=list[ResearchContextRead])
async def list_contexts(session: AsyncSession = Depends(get_session)) -> list[ResearchContextRead]:
    return await ResearchContextService(session).list_contexts()


@router.get("/{context_id}", response_model=ResearchContextRead)
async def get_context(
    context_id: int, session: AsyncSession = Depends(get_session)
) -> ResearchContextRead:
    return await ResearchContextService(session).get(context_id)


@router.patch("/{context_id}", response_model=ResearchContextRead)
async def update_context(
    context_id: int,
    payload: ResearchContextUpdate,
    session: AsyncSession = Depends(get_session),
) -> ResearchContextRead:
    return await ResearchContextService(session).update(context_id, payload)


@router.post("/{context_id}/documents", response_model=ResearchContextRead)
async def add_context_documents(
    context_id: int,
    payload: ResearchContextDocumentAdd,
    session: AsyncSession = Depends(get_session),
) -> ResearchContextRead:
    return await ResearchContextService(session).add_documents(context_id, payload.document_ids)
