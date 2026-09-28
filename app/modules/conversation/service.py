from __future__ import annotations

import asyncio
import builtins
import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.common.logger import logger
from app.core.config import settings
from app.integrations.paperqa2 import (
    PaperQA2Client,
    PaperQAIndex,
    create_paperqa2_client,
)
from app.integrations.paperqa2.exceptions import (
    PaperQA2Error,
    PaperQA2IndexNotFoundError,
)
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
    ReaderContext,
)
from app.modules.document.repository import DocumentRepository
from app.modules.model_config.repository import ModelConfigRepository
from app.modules.research_context.service import ResearchContextService
from app.rag.exceptions import GroundedGenerationError
from app.rag.schemas import EvidenceSet, GroundedAnswer

MAX_EVIDENCE_LENGTH = 2000
_LOCKS: dict[int, asyncio.Lock] = {}


class EvidenceProvider(Protocol):
    async def evidence_for(self, question: str, document_ids: list[int]) -> EvidenceSet: ...


class GroundedAnswerProvider(Protocol):
    async def answer(self, evidence: EvidenceSet) -> GroundedAnswer: ...


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], PaperQA2Client] | None = None,
        evidence_provider: EvidenceProvider | None = None,
        grounded_answer_provider: GroundedAnswerProvider | None = None,
        grounded_mode: str | None = None,
        shadow_status_callback: Callable[[str], None] | None = None,
    ):
        self.session = session
        self.repo = ConversationRepository(session)
        self.documents = DocumentRepository(session)
        self.model_configs = ModelConfigRepository(session)
        self.research_contexts = ResearchContextService(session)
        self.client_factory = client_factory
        self.evidence_provider = evidence_provider
        self.grounded_answer_provider = grounded_answer_provider
        configured_mode = grounded_mode or settings.GROUNDED_RAG_MODE
        # 显式注入仅供受控测试/内部 shadow；默认配置关闭时立即保持旧 PaperQA2 链路。
        self.grounded_mode = (
            configured_mode
            if grounded_mode is not None or settings.GROUNDED_RAG_ENABLED
            else "paperqa"
        )
        self.shadow_status_callback = shadow_status_callback

    async def _paperqa_client(self) -> tuple[PaperQA2Client, str]:
        """Prefer the saved default local model; keep injected clients for tests."""
        if self.client_factory is not None:
            return self.client_factory(), self._model_version()
        configured = await self.model_configs.default_local()
        if configured is not None:
            client = create_paperqa2_client(
                provider="ollama",
                model=configured.model_name,
                base_url=configured.api_base,
            )
            return client, f"ollama:{configured.model_name};{POLICY_VERSION}"
        return create_paperqa2_client(), self._model_version()

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

    async def ask(
        self, id: int, question: str, reader_context: ReaderContext | None = None
    ):
        if reader_context is not None:
            entity = await self.repo.get(id)
            if entity is None:
                raise NotFoundError(f"Conversation not found: {id}")
            if reader_context.document_id not in (self._decode_document_ids(entity) or []):
                raise ConflictError("Reader context document is outside this conversation")
        if self.grounded_mode == "grounded":
            if self.evidence_provider is None or self.grounded_answer_provider is None:
                raise ConflictError("Grounded answering requires evidence and answer providers")
            return await self._ask_grounded(id, question, reader_context)
        answer = await self._ask_paperqa(id, question, reader_context)
        if self.grounded_mode == "shadow":
            entity = await self.repo.get(id)
            document_ids = self._decode_document_ids(entity) if entity is not None else []
            await self._run_grounded_shadow(question, document_ids or [])
        return answer

    async def _run_grounded_shadow(
        self, question: str, document_ids: builtins.list[int]
    ) -> None:
        if self.evidence_provider is None or self.grounded_answer_provider is None:
            if self.shadow_status_callback is not None:
                self.shadow_status_callback("unavailable")
            return
        try:
            evidence = await self.evidence_provider.evidence_for(question, document_ids)
            await self.grounded_answer_provider.answer(evidence)
            if self.shadow_status_callback is not None:
                self.shadow_status_callback("completed")
        except (ConflictError, GroundedGenerationError, ValueError):
            if self.shadow_status_callback is not None:
                self.shadow_status_callback("failed")

    async def _ask_paperqa(
        self, id: int, question: str, reader_context: ReaderContext | None
    ):
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
                    **self._reader_context_values(reader_context),
                    created_at=datetime.now(UTC),
                )
            )
            started = perf_counter()
            answers = []
            try:
                client, model_version = await self._paperqa_client()
                for document in documents:
                    index = PaperQAIndex(
                        index_id=document.paperqa_index_key,
                        document_count=1,
                        reused=True,
                    )
                    prompt = (
                        "Answer only from the indexed paper. Respond in the same language as "
                        "the user's question; when the question is Chinese, respond in Simplified "
                        "Chinese. Keep paper titles, terminology, and citations faithful to the "
                        "source. If evidence is insufficient, say so explicitly. Question: "
                        + question
                    )
                    try:
                        answer = await client.ask(index, prompt)
                    except PaperQA2IndexNotFoundError:
                        # PaperQA2 索引对象驻留进程内存。服务重启后数据库的 index key
                        # 仍有效，但热缓存为空，因此按冻结文档版本重建一次后再回答。
                        from app.modules.document.index_service import DocumentIndexService

                        await DocumentIndexService(
                            self.session,
                            client_factory=lambda: client,
                        ).index(document.id, force_rebuild=True)
                        answer = await client.ask(index, prompt)
                    answers.append((document, answer))
            except PaperQA2Error as exc:
                await self.repo.create(
                    Message(
                        conversation_id=id,
                        sequence=sequence + 1,
                        role="assistant",
                        content="问答系统暂时失败，请稍后重试。",
                        model_version=model_version,
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
                    model_version=model_version,
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
                                **self._citation_context_values(
                                    reader_context, document.id
                                ),
                            )
                        )
            except Exception as exc:
                await self.repo.session.delete(assistant)
                await self.repo.session.flush()
                raise ConflictError("Answer citations could not be saved") from exc
            entity.updated_at = datetime.now(UTC)
            await self.repo.save(entity)
            return await self._message(assistant)

    async def _ask_grounded(
        self, id: int, question: str, reader_context: ReaderContext | None
    ):
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
            allowed_ids = {document.id for document in documents}
            evidence = await self.evidence_provider.evidence_for(  # type: ignore[union-attr]
                question, list(allowed_ids)
            )
            answer = await self.grounded_answer_provider.answer(evidence)  # type: ignore[union-attr]
            evidence_by_chunk = {item.chunk_id: item for item in evidence.evidence}
            for citation in answer.citations:
                if (
                    citation.database_document_id not in allowed_ids
                    or citation.chunk_id not in evidence_by_chunk
                ):
                    raise ConflictError(
                        "Grounded citation is missing or outside authorized evidence"
                    )
                if evidence_by_chunk[citation.chunk_id].document_id != citation.document_id:
                    raise ConflictError("Grounded citation identity does not match evidence")

            sequence = await self.repo.next_sequence(id)
            user = await self.repo.create(
                Message(
                    conversation_id=id,
                    sequence=sequence,
                    role="user",
                    content=question.strip(),
                    **self._reader_context_values(reader_context),
                    created_at=datetime.now(UTC),
                )
            )
            assistant: Message | None = None
            citations: list[Citation] = []
            try:
                assistant = await self.repo.create(
                    Message(
                        conversation_id=id,
                        sequence=sequence + 1,
                        role="assistant",
                        content=answer.answer,
                        model_version=answer.model_version,
                        answer_status=answer.evidence_status,
                        uncertainty=1.0 if answer.fallback else 0.2,
                        reason_codes=json.dumps([]),
                        created_at=datetime.now(UTC),
                    )
                )
                for citation in answer.citations:
                    if citation.database_document_id is None:
                        raise ConflictError("Grounded citation is missing a document identity")
                    citation_document_id = citation.database_document_id
                    persisted = await self.repo.create(
                        Citation(
                            message_id=assistant.id,
                            document_id=citation_document_id,
                            evidence_type="grounded",
                            page=citation.page_number,
                            section=None,
                            evidence_text=evidence_by_chunk[citation.chunk_id].text_original[
                                :MAX_EVIDENCE_LENGTH
                            ],
                            citation_text=citation.source_path,
                            retrieval_score=None,
                            **self._citation_context_values(
                                reader_context, citation_document_id
                            ),
                        )
                    )
                    citations.append(persisted)
                entity.updated_at = datetime.now(UTC)
                await self.repo.save(entity)
            except (ConflictError, GroundedGenerationError, SQLAlchemyError, ValueError) as exc:
                for citation in citations:
                    await self.repo.session.delete(citation)
                if assistant is not None:
                    await self.repo.session.delete(assistant)
                await self.repo.session.delete(user)
                await self.repo.session.flush()
                raise ConflictError("Grounded answer could not be saved") from exc
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
    def _reader_context_values(context: ReaderContext | None) -> dict[str, int | None]:
        if context is None:
            return {}
        return {
            "reader_document_id": context.document_id,
            "reader_source_anchor_id": context.source_anchor_id,
            "reader_active_segment_id": context.active_segment_id,
            "reader_section_id": context.section_id,
            "reader_anchor_revision_id": context.expected_anchor_revision_id,
            "reader_segmentation_revision_id": context.expected_segmentation_revision_id,
        }

    @staticmethod
    def _citation_context_values(
        context: ReaderContext | None, document_id: int
    ) -> dict[str, int | str]:
        if context is None or context.source_anchor_id is None or context.document_id != document_id:
            return {}
        return {
            "source_anchor_id": context.source_anchor_id,
            "anchor_status": "reader_context",
        }

    @staticmethod
    def _model_version():
        value = {
            "openai": settings.OPENAI_MODEL,
            "openrouter": settings.OPENROUTER_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }[settings.DEFAULT_MODEL_PROVIDER]
        return f"{settings.DEFAULT_MODEL_PROVIDER}:{value or 'unconfigured'};{POLICY_VERSION}"
