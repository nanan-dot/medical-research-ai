"""资料范围和阅读锚点在路由之前验证，历史保持来源身份。"""

import json
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.conversation.model import Conversation, Message
from app.modules.conversation.schema import MessageCreate, ReaderContext
from app.modules.document.model import Document
from app.modules.document_reader.copilot import validate_copilot_context
from app.modules.research_context.service import ResearchContextService
from app.modules.unified_conversation.general_answer_service import History


def document_ids(entity: Conversation) -> list[int]:
    try:
        result = json.loads(entity.document_ids)
    except (ValueError, TypeError) as error:
        raise ConflictError("会话资料范围不可用") from error
    if not isinstance(result, list) or not all(
        type(value) is int and value > 0 for value in result
    ):
        raise ConflictError("会话资料范围不可用")
    return result


def source_type(message: Message) -> str:
    if message.role == "user":
        return "user"
    try:
        codes = json.loads(message.reason_codes or "[]")
    except (ValueError, TypeError):
        return "legacy_unknown"
    if isinstance(codes, list):
        for code in codes:
            if code in {
                "source:general",
                "source:paper_grounded",
                "source:mixed",
                "source:web_augmented",
            }:
                return code.removeprefix("source:")
    return "legacy_unknown"


def build_history(messages: list[Message]) -> History:
    return [
        (
            cast(Literal["user", "assistant"], item.role),
            json.dumps(
                {"source": source_type(item), "text": item.content[:6000]},
                ensure_ascii=False,
            ),
        )
        for item in messages[-8:]
        if item.role in {"user", "assistant"}
    ]


async def validate_scope(
    session: AsyncSession,
    ids: list[int],
    context_id: int | None,
    reader: ReaderContext | None = None,
) -> None:
    if len(set(ids)) != len(ids):
        raise ConflictError("Document IDs must be unique")
    for document_id in ids:
        if await session.get(Document, document_id) is None:
            raise NotFoundError(f"文献不存在：{document_id}")
    if context_id is not None:
        await ResearchContextService(session).require_document_membership(
            context_id, ids
        )
    if reader is not None:
        try:
            await validate_copilot_context(
                session,
                MessageCreate(question="context", **reader.model_dump()),
                set(ids),
            )
        except ValueError as error:
            raise ConflictError("阅读锚点上下文不完整") from error
