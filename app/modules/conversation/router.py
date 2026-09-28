from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.conversation.schema import (
    ConversationCreate,
    ConversationRead,
    ConversationSummary,
    FeedbackCreate,
    MessageCreate,
    MessageRead,
)
from app.modules.conversation.service import ConversationService
from app.modules.document_reader.copilot import validate_copilot_context

router = APIRouter(prefix="/conversations", tags=["会话"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(session: AsyncSession = Depends(get_session)):
    return await ConversationService(session).list()


@router.post("", response_model=ConversationRead)
async def create_conversation(
    request: ConversationCreate, session: AsyncSession = Depends(get_session)
):
    return await ConversationService(session).create(
        request.document_ids, request.title, request.research_context_id
    )


@router.get("/latest", response_model=ConversationRead)
async def get_latest_conversation(
    document_id: int = Query(ge=1),
    session: AsyncSession = Depends(get_session),
) -> ConversationRead:
    return await ConversationService(session).latest_for_document(document_id)


@router.get("/{id}", response_model=ConversationRead)
async def get_conversation(id: int, session: AsyncSession = Depends(get_session)):
    return await ConversationService(session).get(id)


@router.post("/{id}/messages", response_model=MessageRead)
async def create_message(
    id: int, request: MessageCreate, session: AsyncSession = Depends(get_session)
):
    service = ConversationService(session)
    conversation = await service.get(id)
    await validate_copilot_context(session, request, set(conversation.document_ids))
    return await service.ask(id, request.question, request.reader_context())


@router.post("/{id}/messages/{message_id}/feedback", response_model=MessageRead)
async def feedback(
    id: int,
    message_id: int,
    request: FeedbackCreate,
    session: AsyncSession = Depends(get_session),
):
    return await ConversationService(session).feedback(id, message_id, request.rating)


@router.delete("/{id}", status_code=204)
async def delete_conversation(id: int, session: AsyncSession = Depends(get_session)):
    await ConversationService(session).delete(id)
