"""统一轮次：先验证范围、再分类执行，最后原子保存答案与来源。"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AppError, ConflictError, NotFoundError
from app.integrations.llm.exceptions import LLMClientError
from app.modules.conversation.model import Conversation
from app.modules.conversation.repository import ConversationRepository
from app.modules.unified_conversation.context import (
    build_history,
    document_ids,
    source_type,
    validate_scope,
)
from app.modules.unified_conversation.executor import (
    AnswerExecutor,
    ExternalProvider,
    GeneralProvider,
    PaperProvider,
)
from app.modules.unified_conversation.external_answer_service import (
    ExternalAnswerService,
)
from app.modules.unified_conversation.general_answer_service import (
    GeneralAnswer,
    GeneralAnswerService,
)
from app.modules.unified_conversation.model import KnowledgeGap, UnifiedTurn
from app.modules.unified_conversation.paper_answer_service import PaperAnswerService
from app.modules.unified_conversation.query_router import QueryRouter, RouteDecision
from app.modules.unified_conversation.repository import TurnRepository
from app.modules.unified_conversation.schema import (
    AnswerMode,
    GapRead,
    UnifiedAnswerRead,
    UnifiedCitationRead,
    UnifiedConversationCreate,
    UnifiedConversationRead,
    UnifiedMessageCreate,
    UnifiedMessageRead,
)

__all__ = ["GeneralAnswer", "UnifiedConversationService"]
logger = logging.getLogger(__name__)


class UnifiedConversationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        general_answer_service: GeneralProvider | None = None,
        query_router: QueryRouter | None = None,
        paper_answer_service: PaperProvider | None = None,
        external_answer_service: ExternalProvider | None = None,
    ) -> None:
        self.session = session
        self.repository = ConversationRepository(session)
        self.turns = TurnRepository(session)
        model = GeneralAnswerService(session)
        self.executor = AnswerExecutor(
            general_answer_service or model,
            paper_answer_service or PaperAnswerService(session),
            external_answer_service or ExternalAnswerService(),
        )
        self.query_router = query_router or QueryRouter(model)

    async def create(
        self, payload: UnifiedConversationCreate
    ) -> UnifiedConversationRead:
        await validate_scope(
            self.session, payload.document_ids, payload.research_context_id
        )
        now = datetime.now(UTC)
        entity = await self.repository.create(
            Conversation(
                document_ids=json.dumps(payload.document_ids),
                title=payload.title,
                research_context_id=payload.research_context_id,
                created_at=now,
                updated_at=now,
            )
        )
        return await self.get(entity.id)

    async def get(self, conversation_id: int) -> UnifiedConversationRead:
        entity = await self._require(conversation_id)
        runs = list(
            (
                await self.session.scalars(
                    select(UnifiedTurn).where(
                        UnifiedTurn.conversation_id == conversation_id
                    )
                )
            ).all()
        )
        answers = {
            run.assistant_message_id: UnifiedAnswerRead.model_validate_json(
                run.response_json
            )
            for run in runs
            if run.response_json
        }
        messages = []
        for message in await self.repository.messages(conversation_id):
            answer = answers.get(message.id)
            citations = [
                UnifiedCitationRead.model_validate(item, from_attributes=True)
                for item in await self.repository.citations(message.id)
            ]
            messages.append(
                UnifiedMessageRead(
                    id=message.id,
                    sequence=message.sequence,
                    role=message.role,
                    content=message.content,
                    source_type=source_type(message),
                    answer_status=message.answer_status,
                    created_at=message.created_at,
                    citations=answer.citations if answer else citations,
                    sections=answer.sections if answer else [],
                    warnings=answer.warnings if answer else [],
                )
            )
        return UnifiedConversationRead(
            id=entity.id,
            document_ids=document_ids(entity),
            title=entity.title,
            research_context_id=entity.research_context_id,
            messages=messages,
        )

    async def ask(
        self, conversation_id: int, payload: UnifiedMessageCreate
    ) -> UnifiedAnswerRead:
        entity = await self._require(conversation_id)
        ids = (
            payload.document_ids
            if payload.document_ids is not None
            else document_ids(entity)
        )
        await validate_scope(
            self.session, ids, entity.research_context_id, payload.reader_context
        )
        previous = await self.repository.messages(conversation_id)
        history = build_history(previous)
        last_assistant = next(
            (item for item in reversed(previous) if item.role == "assistant"), None
        )
        paper_history = last_assistant is not None and source_type(last_assistant) in {
            "paper_grounded",
            "mixed",
        }
        turn, fresh = await self.turns.claim(conversation_id, payload)
        if not fresh:
            if turn.response_json:
                return UnifiedAnswerRead.model_validate_json(turn.response_json)
            raise ConflictError("此请求仍在处理，请查询状态或取消")
        started = perf_counter()
        try:
            async with asyncio.timeout(300):
                route = await self.query_router.resolve(
                    payload.message,
                    payload.mode,
                    has_documents=bool(ids),
                    has_paper_history=paper_history,
                    history=history,
                )
                if payload.scope_type == "library":
                    route = RouteDecision(
                        AnswerMode.PAPER_GROUNDED, "library_scope_unavailable", True
                    )
                paper_question = payload.message
                if route.reason_code == "paper_history_reference":
                    last_question = next(
                        (
                            item.content
                            for item in reversed(previous)
                            if item.role == "user"
                        ),
                        "",
                    )
                    paper_question = (
                        "用户上一个问题："
                        + last_question
                        + "\n用户追问："
                        + payload.message
                    )
                mode, content = await self.executor.run(
                    payload, route, ids, history, paper_question
                )
                # 外部服务和分类结果都不能扩大实际文献范围或传入伪引用。
                if any(
                    citation.document_id is not None and citation.document_id not in ids
                    for section in content.sections
                    for citation in section.citations
                ):
                    raise ConflictError("回答引用超出本次授权资料范围")
                warnings = list(dict.fromkeys(content.warnings))
                response = UnifiedAnswerRead(
                    conversation_id=conversation_id,
                    message_id=0,
                    answer="\n\n".join(section.content for section in content.sections),
                    answer_mode=mode,
                    answer_status=content.status,
                    route_reason_code=route.reason_code,
                    scope_used=content.scope_used,
                    sections=content.sections,
                    citations=[
                        citation
                        for section in content.sections
                        for citation in section.citations
                        if section.source_type != "general"
                    ],
                    warnings=warnings,
                    suggested_actions=list(dict.fromkeys(content.actions)),
                    latency_ms=int((perf_counter() - started) * 1000),
                )
                evidence_gap = {
                    "insufficient_evidence",
                    "partial_evidence",
                }.intersection(warnings)
                failures = {
                    "retrieval_failure",
                    "generation_failure",
                    "web_failure",
                    "index_not_ready",
                    "index_failure",
                    "parse_failure",
                }
                if (
                    evidence_gap
                    and content.scope_used
                    and not failures.intersection(warnings)
                ):
                    await self.turns.gap(
                        payload.message, content.scope_used, entity.research_context_id
                    )
                response = await self.turns.finish(turn, response)
                logger.info(
                    "unified_chat trace=%s route=%s scope=%s elapsed_ms=%d codes=%s",
                    response.trace_id,
                    route.reason_code,
                    content.scope_used,
                    response.latency_ms,
                    warnings,
                )
                return response
        except asyncio.CancelledError:
            await self.session.rollback()
            current = await self.turns.find(conversation_id, payload.request_id)
            if current is not None and current.state == "running":
                await self.turns.finish(
                    current,
                    self.turns.failure(current, "cancelled"),
                    allow_expired=True,
                )
            raise
        except (LLMClientError, AppError, TimeoutError):
            await self.session.rollback()
            current = await self.turns.find(conversation_id, payload.request_id)
            if current is not None and current.state == "running":
                return await self.turns.finish(
                    current,
                    self.turns.failure(current, "generation_failure"),
                    allow_expired=True,
                )
            raise

    async def cancel(self, conversation_id: int, request_id: str) -> UnifiedAnswerRead:
        await self._require(conversation_id)
        turn = await self.turns.find(conversation_id, request_id)
        if turn is None:
            raise NotFoundError("请求不存在")
        if turn.response_json:
            return UnifiedAnswerRead.model_validate_json(turn.response_json)
        return await self.turns.finish(
            turn, self.turns.failure(turn, "cancelled"), allow_expired=True
        )

    async def gaps(self) -> list[GapRead]:
        rows = (
            await self.session.scalars(
                select(KnowledgeGap).order_by(KnowledgeGap.id.desc()).limit(100)
            )
        ).all()
        return [
            GapRead(
                id=row.id,
                question=row.question,
                document_ids=json.loads(row.document_ids),
                research_context_id=row.research_context_id,
                occurrences=row.occurrences,
            )
            for row in rows
        ]

    async def delete_gap(self, gap_id: int) -> None:
        gap = await self.session.get(KnowledgeGap, gap_id)
        if gap is None:
            raise NotFoundError("知识缺口不存在")
        await self.session.delete(gap)
        await self.session.flush()

    async def _require(self, conversation_id: int) -> Conversation:
        entity = await self.repository.get(conversation_id)
        if entity is None:
            raise NotFoundError("会话不存在")
        return entity
