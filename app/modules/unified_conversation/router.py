"""统一科研对话非流式 API；断线取消，已完成请求可按编号恢复。"""

import asyncio
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError, TemporarilyUnavailableError
from app.core.database import get_session
from app.modules.unified_conversation.schema import (
    GapRead,
    UnifiedAnswerRead,
    UnifiedConversationCreate,
    UnifiedConversationRead,
    UnifiedMessageCreate,
)
from app.modules.unified_conversation.service import UnifiedConversationService

router = APIRouter(prefix="/unified-conversations", tags=["统一科研对话"])


async def ready(session: AsyncSession) -> bool:
    connection = await session.connection()
    return await connection.run_sync(
        lambda conn: (
            inspect(conn).has_table("unified_chat_turns")
            and inspect(conn).has_table("unified_knowledge_gaps")
        )
    )


async def chat_service(
    session: AsyncSession = Depends(get_session),
) -> UnifiedConversationService:
    if not await ready(session):
        raise TemporarilyUnavailableError(
            "统一对话需要先完成数据库升级；本接口不会自动迁移现有数据库。"
        )
    return UnifiedConversationService(session)


@router.get("/capabilities")
async def capabilities(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return {
        "migration_ready": await ready(session),
        "streaming": False,
        "full_library": False,
        "selected_document_limit": 10,
        "external_source": "PubMed",
        "source_levels": ["metadata", "abstract"],
        "identity_scope": "local_single_user",
    }


@router.get("/gaps", response_model=list[GapRead])
async def gaps(
    service: UnifiedConversationService = Depends(chat_service),
) -> list[GapRead]:
    return await service.gaps()


@router.delete("/gaps/{gap_id}", status_code=204)
async def delete_gap(
    gap_id: int, service: UnifiedConversationService = Depends(chat_service)
) -> None:
    await service.delete_gap(gap_id)


@router.get("")
async def list_conversations(
    service: UnifiedConversationService = Depends(chat_service),
) -> list[dict[str, object]]:
    return [
        {"id": item.id, "title": item.title}
        for item in (await service.repository.list())[:100]
    ]


@router.post("", response_model=UnifiedConversationRead)
async def create_conversation(
    request: UnifiedConversationCreate,
    service: UnifiedConversationService = Depends(chat_service),
) -> UnifiedConversationRead:
    return await service.create(request)


@router.get("/{conversation_id}", response_model=UnifiedConversationRead)
async def get_conversation(
    conversation_id: int, service: UnifiedConversationService = Depends(chat_service)
) -> UnifiedConversationRead:
    return await service.get(conversation_id)


@router.get("/{conversation_id}/requests/{request_id}")
async def request_status(
    conversation_id: int,
    request_id: str,
    service: UnifiedConversationService = Depends(chat_service),
) -> dict[str, object]:
    turn = await service.turns.find(conversation_id, request_id)
    if turn is None:
        raise NotFoundError("请求不存在")
    if turn.state == "running" and turn.deadline < time.time():
        await service.turns.finish(
            turn, service.turns.failure(turn, "generation_failure"), allow_expired=True
        )
    return {
        "state": turn.state,
        "response": UnifiedAnswerRead.model_validate_json(turn.response_json)
        if turn.response_json
        else None,
    }


@router.post(
    "/{conversation_id}/requests/{request_id}/cancel", response_model=UnifiedAnswerRead
)
async def cancel_request(
    conversation_id: int,
    request_id: str,
    service: UnifiedConversationService = Depends(chat_service),
) -> UnifiedAnswerRead:
    return await service.cancel(conversation_id, request_id)


async def wait_for_disconnect(request: Request) -> None:
    while not await request.is_disconnected():
        await asyncio.sleep(0.2)


@router.post("/{conversation_id}/messages", response_model=UnifiedAnswerRead)
async def create_message(
    conversation_id: int,
    request: Request,
    payload: UnifiedMessageCreate,
    service: UnifiedConversationService = Depends(chat_service),
) -> UnifiedAnswerRead:
    work = asyncio.create_task(service.ask(conversation_id, payload))
    disconnected = asyncio.create_task(wait_for_disconnect(request))
    try:
        done, _ = await asyncio.wait(
            {work, disconnected}, return_when=asyncio.FIRST_COMPLETED
        )
        if work in done:
            return await work
        work.cancel()
        await asyncio.gather(work, return_exceptions=True)
        raise TemporarilyUnavailableError("客户端已断开，请按请求编号查询结果。")
    finally:
        disconnected.cancel()
        if not work.done():
            work.cancel()
        await asyncio.gather(disconnected, work, return_exceptions=True)
