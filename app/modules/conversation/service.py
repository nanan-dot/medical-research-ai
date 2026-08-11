from __future__ import annotations

import asyncio
import builtins
import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.common.logger import logger
from app.core.config import settings
from app.integrations.paperqa2 import (
    PaperQA2Client,
    PaperQAIndex,
    create_paperqa2_client,
)
from app.integrations.paperqa2.exceptions import PaperQA2Error
from app.modules.conversation.model import Citation, Conversation, Message
from app.modules.conversation.no_answer import (
    NO_ANSWER_TEXT,
    POLICY_VERSION,
    evaluate_answer,
)
from app.modules.conversation.repository import ConversationRepository
from app.modules.conversation.schema import (
    CitationRead,
    ConversationRead,
    ConversationSummary,
    MessageRead,
)
from app.modules.document.repository import DocumentRepository
from app.modules.research_context.service import ResearchContextService

MAX_EVIDENCE_LENGTH = 2000
_LOCKS: dict[int, asyncio.Lock] = {}


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], PaperQA2Client] | None = None,
    ):
        self.repo = ConversationRepository(session)
        self.documents = DocumentRepository(session)
        self.research_contexts = ResearchContextService(session)
        self.client_factory = client_factory or create_paperqa2_client

    async def create(
        self,
        document_ids: list[int],
        title: str | None = None,
        research_context_id: int | None = None,
    ):
        unique = list(dict.fromkeys(document_ids))
        for document_id in unique:
            await self._indexed(document_id)
        if research_context_id is not None:
            await self.research_contexts.require_document_membership(
                research_context_id, unique
            )
        now = datetime.now(UTC)
        entity = await self.repo.create(
            Conversation(
                document_ids=json.dumps(unique),
                title=title,
                research_context_id=research_context_id,
                created_at=now,
                updated_at=now,
            )
        )
        return await self._read(entity)

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Conversation not found: {id}")
        return await self._read(entity)

    async def latest_for_document(self, document_id: int) -> ConversationRead:
        for entity in await self.repo.latest_candidates():
            document_ids = self._decode_document_ids(entity)
            if document_ids == [document_id]:
                return await self._read(entity)
        raise NotFoundError(f"Conversation not found for document: {document_id}")

    async def list(self):
        result = []
        for entity in await self.repo.list():
            result.append(
                ConversationSummary(
                    id=entity.id,
                    document_ids=json.loads(entity.document_ids),
                    title=entity.title,
                    research_context_id=entity.research_context_id,
                    updated_at=entity.updated_at,
                    message_count=len(await self.repo.messages(entity.id)),
                )
            )
        return result

    async def delete(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Conversation not found: {id}")
        await self.repo.delete(entity)

    async def ask(self, id: int, question: str):
        lock = _LOCKS.setdefault(id, asyncio.Lock())
        if lock.locked():
            raise ConflictError("A conversation message is already being processed")
        async with lock:
            entity = await self.repo.get(id)
            if entity is None:
                raise NotFoundError(f"Conversation not found: {id}")
            documents = [
                await self._indexed(value) for value in json.loads(entity.document_ids)
            ]
            sequence = await self.repo.next_sequence(id)
            await self.repo.create(
                Message(
                    conversation_id=id,
                    sequence=sequence,
                    role="user",
                    content=question.strip(),
                    created_at=datetime.now(UTC),
                )
            )
            started = perf_counter()
            answers = []
            try:
                client = self.client_factory()
                for document in documents:
                    answer = await client.ask(
                        PaperQAIndex(
                            index_id=document.paperqa_index_key,
                            document_count=1,
                            reused=True,
                        ),
                        "Answer only from the indexed paper. If evidence is insufficient, say so explicitly. Question: "
                        + question,
                    )
                    answers.append((document, answer))
            except PaperQA2Error as exc:
                await self.repo.create(
                    Message(
                        conversation_id=id,
                        sequence=sequence + 1,
                        role="assistant",
                        content="问答系统暂时失败，请稍后重试。",
                        model_version=self._model_version(),
                        latency_ms=int((perf_counter() - started) * 1000),
                        answer_status="failed",
                        uncertainty=1.0,
                        reason_codes=json.dumps(["system_error"]),
                        created_at=datetime.now(UTC),
                    )
                )
                raise ConflictError("Paper question answering failed") from exc
            decision = evaluate_answer([answer for _, answer in answers])
            content = (
                NO_ANSWER_TEXT
                if decision.status == "insufficient_evidence"
                else "\n\n".join(answer.answer for _, answer in answers)
            )
            assistant = await self.repo.create(
                Message(
                    conversation_id=id,
                    sequence=sequence + 1,
                    role="assistant",
                    content=content,
                    model_version=self._model_version(),
                    latency_ms=int((perf_counter() - started) * 1000),
                    answer_status=decision.status,
                    uncertainty=decision.uncertainty,
                    reason_codes=json.dumps(decision.reason_codes),
                    created_at=datetime.now(UTC),
                )
            )
            try:
                for document, answer in answers:
                    for source in answer.sources:
                        await self.repo.create(
                            Citation(
                                message_id=assistant.id,
                                document_id=document.id,
                                evidence_type="paperqa",
                                page=source.page_start,
                                section=source.title,
                                evidence_text=(source.excerpt or "")[
                                    :MAX_EVIDENCE_LENGTH
                                ]
                                or None,
                                citation_text=source.citation,
                                retrieval_score=source.score,
                            )
                        )
            except Exception as exc:
                await self.repo.session.delete(assistant)
                await self.repo.session.flush()
                raise ConflictError("Answer citations could not be saved") from exc
            entity.updated_at = datetime.now(UTC)
            await self.repo.save(entity)
            return await self._message(assistant)

    async def feedback(self, conversation_id: int, message_id: int, rating: int):
        message = await self.repo.session.get(Message, message_id)
        if (
            message is None
            or message.conversation_id != conversation_id
            or message.role != "assistant"
        ):
            raise NotFoundError("Assistant message not found")
        message.feedback = rating
        await self.repo.save(message)
        return await self._message(message)

    async def _indexed(self, id: int):
        document = await self.documents.get(id)
        if document is None:
            raise NotFoundError(f"Document not found: {id}")
        if document.index_status != "succeeded" or not document.paperqa_index_key:
            raise ConflictError(
                "All selected documents must have current successful indexes"
            )
        return document

    async def _read(self, entity):
        return ConversationRead(
            id=entity.id,
            document_ids=json.loads(entity.document_ids),
            title=entity.title,
            research_context_id=entity.research_context_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            messages=[
                await self._message(item)
                for item in await self.repo.messages(entity.id)
            ],
        )

    @staticmethod
    def _decode_document_ids(entity: Conversation) -> builtins.list[int] | None:
        try:
            parsed_ids = json.loads(entity.document_ids)
        except json.JSONDecodeError:
            logger.warning("Skipping conversation with invalid document_ids JSON: %s", entity.id)
            return None
        if not isinstance(parsed_ids, list) or not all(
            isinstance(document_id, int) and not isinstance(document_id, bool)
            for document_id in parsed_ids
        ):
            logger.warning("Skipping conversation with invalid document_ids value: %s", entity.id)
            return None
        return parsed_ids

    async def _message(self, entity):
        return MessageRead(
            id=entity.id,
            sequence=entity.sequence,
            role=entity.role,
            content=entity.content,
            model_version=entity.model_version,
            latency_ms=entity.latency_ms,
            feedback=entity.feedback,
            answer_status=entity.answer_status,
            uncertainty=entity.uncertainty,
            reason_codes=json.loads(entity.reason_codes or "[]"),
            created_at=entity.created_at,
            citations=[
                CitationRead.model_validate(item, from_attributes=True)
                for item in await self.repo.citations(entity.id)
            ],
        )

    @staticmethod
    def _model_version():
        value = {
            "openai": settings.OPENAI_MODEL,
            "openrouter": settings.OPENROUTER_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }[settings.DEFAULT_MODEL_PROVIDER]
        return f"{settings.DEFAULT_MODEL_PROVIDER}:{value or 'unconfigured'};{POLICY_VERSION}"
