import pytest

from app.integrations.llm.exceptions import LLMConnectionError
from app.modules.unified_conversation.query_router import QueryRouter
from app.modules.unified_conversation.schema import (
    AnswerMode,
    ConversationMode,
    UnifiedConversationCreate,
    UnifiedMessageCreate,
)
from app.modules.unified_conversation.service import (
    GeneralAnswer,
    UnifiedConversationService,
)


class FakeGeneralAnswerService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def answer(
        self, question: str, history: list[tuple[str, str]]
    ) -> GeneralAnswer:
        self.calls.append(question)
        return GeneralAnswer(
            content=f"通用回答：{question}", model_version="fake:general"
        )


class FailingGeneralAnswerService:
    async def answer(
        self, question: str, history: list[tuple[str, str]]
    ) -> GeneralAnswer:
        raise LLMConnectionError("offline")


@pytest.mark.asyncio
async def test_general_question_creates_zero_document_conversation_without_paperqa(
    session,
) -> None:
    general = FakeGeneralAnswerService()
    service = UnifiedConversationService(
        session,
        general_answer_service=general,
        query_router=QueryRouter(),
    )

    conversation = await service.create(UnifiedConversationCreate())
    result = await service.ask(conversation.id, UnifiedMessageCreate(message="你好"))

    assert result.answer_mode is AnswerMode.GENERAL
    assert result.answer_status == "answered"
    assert result.citations == []
    assert general.calls == ["你好"]
    restored = await service.get(conversation.id)
    assert restored.document_ids == []
    assert [message.source_type for message in restored.messages] == ["user", "general"]


@pytest.mark.asyncio
async def test_explicit_paper_request_without_scope_returns_clarification(
    session,
) -> None:
    service = UnifiedConversationService(
        session,
        general_answer_service=FakeGeneralAnswerService(),
        query_router=QueryRouter(),
    )
    conversation = await service.create(UnifiedConversationCreate())

    result = await service.ask(
        conversation.id,
        UnifiedMessageCreate(message="这篇论文纳入多少人", mode=ConversationMode.AUTO),
    )

    assert result.answer_mode is AnswerMode.GENERAL
    assert result.route_reason_code == "scope_required"
    assert result.answer_status == "partial"


@pytest.mark.asyncio
async def test_general_generation_failure_is_saved_as_failed_message(session) -> None:
    service = UnifiedConversationService(
        session,
        general_answer_service=FailingGeneralAnswerService(),
        query_router=QueryRouter(),
    )
    conversation = await service.create(UnifiedConversationCreate())

    result = await service.ask(conversation.id, UnifiedMessageCreate(message="你好"))

    assert result.answer_status == "failed"
    assert result.warnings == ["generation_failure"]
    assert (await service.get(conversation.id)).messages[-1].answer_status == "failed"


def test_greeting_plus_paper_request_is_not_classified_as_greeting() -> None:
    decision = QueryRouter().route(
        "你好，请总结这篇论文", ConversationMode.AUTO, has_documents=True
    )

    assert decision.answer_mode is AnswerMode.PAPER_GROUNDED


def test_ambiguous_reference_requires_paper_history() -> None:
    decision = QueryRouter().route(
        "它的结论呢", ConversationMode.AUTO, has_documents=True
    )

    assert decision.reason_code == "scope_required"

    continued = QueryRouter().route(
        "它的结论呢",
        ConversationMode.AUTO,
        has_documents=True,
        has_paper_history=True,
    )

    assert continued.answer_mode is AnswerMode.PAPER_GROUNDED
    assert continued.reason_code == "paper_history_reference"


def test_api_creates_a_zero_document_unified_conversation(client) -> None:
    response = client.post("/api/v1/unified-conversations", json={})

    assert response.status_code == 200
    assert response.json()["document_ids"] == []


# 文献执行与补充的行为测试位于 test_acceptance.py，直接注入 PaperQA2 适配器替身。
