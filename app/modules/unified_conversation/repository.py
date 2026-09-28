"""数据库唯一约束负责跨请求去重；答案和来源在同一事务完成。"""

import hashlib
import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.conversation.model import Citation, Conversation, Message
from app.modules.unified_conversation.model import KnowledgeGap, UnifiedTurn
from app.modules.unified_conversation.schema import (
    AnswerMode,
    UnifiedAnswerRead,
    UnifiedMessageCreate,
)

TURN_TIMEOUT = 330


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class TurnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find(self, conversation_id: int, request_id: str) -> UnifiedTurn | None:
        return await self.session.scalar(
            select(UnifiedTurn).where(
                UnifiedTurn.conversation_id == conversation_id,
                UnifiedTurn.request_id == request_id,
            )
        )

    async def claim(
        self, conversation_id: int, payload: UnifiedMessageCreate
    ) -> tuple[UnifiedTurn, bool]:
        digest = fingerprint(payload.model_dump(mode="json", exclude={"request_id"}))
        existing = await self.find(conversation_id, payload.request_id)
        if existing is not None:
            if existing.fingerprint != digest:
                raise ConflictError("同一个请求编号不能用于不同内容")
            return existing, False
        expired = await self.session.scalar(
            select(UnifiedTurn).where(
                UnifiedTurn.active_key == conversation_id,
                UnifiedTurn.deadline < time.time(),
            )
        )
        if expired is not None:
            await self.finish(
                expired, self.failure(expired, "generation_failure"), allow_expired=True
            )
        try:
            async with self.session.begin_nested():
                # active_key 的唯一性覆盖所有进程；成功和失败都只创建一个助手消息。
                turn = UnifiedTurn(
                    conversation_id=conversation_id,
                    request_id=payload.request_id,
                    fingerprint=digest,
                    trace_id=uuid4().hex,
                    active_key=conversation_id,
                    deadline=time.time() + TURN_TIMEOUT,
                    state="running",
                    user_message_id=0,
                )
                from sqlalchemy import func

                sequence = (
                    int(
                        await self.session.scalar(
                            select(func.max(Message.sequence)).where(
                                Message.conversation_id == conversation_id
                            )
                        )
                        or 0
                    )
                    + 1
                )
                user = Message(
                    conversation_id=conversation_id,
                    sequence=sequence,
                    role="user",
                    content=payload.message,
                    reason_codes='["source:user"]',
                    created_at=datetime.now(UTC),
                )
                self.session.add(user)
                await self.session.flush()
                turn.user_message_id = user.id
                self.session.add(turn)
                await self.session.flush()
                if payload.document_ids is not None:
                    conversation = await self.session.get(Conversation, conversation_id)
                    if conversation is not None:
                        conversation.document_ids = json.dumps(payload.document_ids)
            await self.session.commit()
            return turn, True
        except IntegrityError as error:
            raise ConflictError("此会话已有请求正在处理，请等待或取消后重试") from error

    async def finish(
        self,
        turn: UnifiedTurn,
        response: UnifiedAnswerRead,
        *,
        allow_expired: bool = False,
    ) -> UnifiedAnswerRead:
        condition = [UnifiedTurn.id == turn.id, UnifiedTurn.state == "running"]
        if not allow_expired:
            condition.append(UnifiedTurn.deadline >= time.time())
        claimed = await self.session.execute(
            update(UnifiedTurn).where(*condition).values(state="finishing")
        )
        if claimed.rowcount != 1:  # type: ignore[attr-defined]
            await self.session.rollback()
            raise ConflictError("请求已结束、取消或超时")
        user = await self.session.get(Message, turn.user_message_id)
        if user is None:
            raise NotFoundError("请求对应的用户消息不存在")
        assistant = Message(
            conversation_id=turn.conversation_id,
            sequence=user.sequence + 1,
            role="assistant",
            content=response.answer,
            answer_status=response.answer_status,
            latency_ms=response.latency_ms,
            reason_codes=json.dumps(
                [
                    f"source:{response.answer_mode.value}",
                    f"route:{response.route_reason_code}",
                    *response.warnings,
                ]
            ),
            created_at=datetime.now(UTC),
        )
        self.session.add(assistant)
        await self.session.flush()
        response.message_id = assistant.id
        response.request_id = turn.request_id
        response.trace_id = turn.trace_id
        for citation in response.citations:
            if citation.document_id is not None:
                self.session.add(
                    Citation(
                        message_id=assistant.id,
                        document_id=citation.document_id,
                        evidence_type="paperqa",
                        page=citation.page,
                        section=citation.section,
                        evidence_text=citation.evidence_text,
                        citation_text=citation.citation_text,
                        source_anchor_id=citation.source_anchor_id,
                        anchor_status=citation.anchor_status,
                    )
                )
        turn.assistant_message_id = assistant.id
        turn.response_json = response.model_dump_json()
        turn.state = "cancelled" if "cancelled" in response.warnings else "completed"
        turn.active_key = None
        conversation = await self.session.get(Conversation, turn.conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.now(UTC)
        await self.session.commit()
        return response

    @staticmethod
    def failure(turn: UnifiedTurn, code: str) -> UnifiedAnswerRead:
        return UnifiedAnswerRead(
            conversation_id=turn.conversation_id,
            message_id=0,
            answer="请求已取消。"
            if code == "cancelled"
            else "本次请求未能完成，请重试。",
            answer_mode=AnswerMode.GENERAL,
            answer_status="failed",
            route_reason_code=code,
            scope_used=[],
            warnings=[code],
            suggested_actions=["retry"],
        )

    async def gap(self, question: str, ids: list[int], context_id: int | None) -> None:
        # 本地单用户应用不接收前端伪造 user_id；范围和研究上下文共同确定去重身份。
        normalized = " ".join(question.casefold().split())
        digest = fingerprint(["local", context_id, sorted(ids), normalized])
        from sqlalchemy.dialects.sqlite import insert

        statement = insert(KnowledgeGap).values(
            fingerprint=digest,
            question=question,
            document_ids=json.dumps(sorted(ids)),
            research_context_id=context_id,
            occurrences=1,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=["fingerprint"],
                set_={"occurrences": KnowledgeGap.occurrences + 1},
            )
        )
