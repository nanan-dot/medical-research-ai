from pathlib import Path

import pytest

from app.common.exceptions import ConflictError, NotFoundError
from app.integrations.paperqa2 import PaperQAAnswer, PaperSource
from app.integrations.paperqa2.exceptions import PaperQA2OperationError
from app.modules.conversation.service import MAX_EVIDENCE_LENGTH, ConversationService
from tests.modules.document.conftest import create_document


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def ask(self, index, question):
        self.calls.append(index.index_id)
        if self.fail:
            raise PaperQA2OperationError("offline")
        return PaperQAAnswer(
            answer=f"Answer from {index.index_id}",
            index_id=index.index_id,
            sources=[
                PaperSource(
                    citation="Paper",
                    page_start=None,
                    excerpt="x" * (MAX_EVIDENCE_LENGTH + 20),
                    score=0.8,
                )
            ],
        )


async def indexed(session, tmp_path: Path, name: str):
    document, _ = await create_document(session, tmp_path / name, f"{name}.pdf")
    document.index_status = "succeeded"
    document.paperqa_index_key = f"idx-{name}"
    await session.commit()
    return document


@pytest.mark.asyncio
async def test_single_document_answer_sources_and_restore(session, tmp_path):
    document = await indexed(session, tmp_path, "one")
    client = FakeClient()
    service = ConversationService(session, client_factory=lambda: client)
    conversation = await service.create([document.id])
    message = await service.ask(conversation.id, "How many?")
    assert message.sequence == 2 and message.citations[0].page is None
    assert len(message.citations[0].evidence_text) == MAX_EVIDENCE_LENGTH
    restored = await service.get(conversation.id)
    assert [item.role for item in restored.messages] == ["user", "assistant"]
    assert restored.messages[1].citations[0].retrieval_score == 0.8


@pytest.mark.asyncio
async def test_selected_documents_are_each_queried(session, tmp_path):
    one = await indexed(session, tmp_path, "one")
    two = await indexed(session, tmp_path, "two")
    client = FakeClient()
    service = ConversationService(session, client_factory=lambda: client)
    conversation = await service.create([one.id, two.id])
    answer = await service.ask(conversation.id, "Compare")
    assert client.calls == ["idx-one", "idx-two"] and len(answer.citations) == 2


@pytest.mark.asyncio
async def test_outdated_document_and_model_failure_are_explicit(session, tmp_path):
    document = await indexed(session, tmp_path, "one")
    service = ConversationService(session, client_factory=lambda: FakeClient(fail=True))
    conversation = await service.create([document.id])
    with pytest.raises(ConflictError, match="failed"):
        await service.ask(conversation.id, "Question")
    document.index_status = "outdated"
    await session.flush()
    with pytest.raises(ConflictError, match="current"):
        await service.create([document.id])


@pytest.mark.asyncio
async def test_feedback_is_saved(session, tmp_path):
    document = await indexed(session, tmp_path, "one")
    service = ConversationService(session, client_factory=FakeClient)
    conversation = await service.create([document.id])
    answer = await service.ask(conversation.id, "Question")
    rated = await service.feedback(conversation.id, answer.id, 1)
    assert rated.feedback == 1


@pytest.mark.asyncio
async def test_latest_single_document_conversation_excludes_multi_document(session, tmp_path):
    one = await indexed(session, tmp_path, "one")
    two = await indexed(session, tmp_path, "two")
    service = ConversationService(session, client_factory=FakeClient)
    single = await service.create([one.id])
    await service.create([one.id, two.id])
    assert (await service.latest_for_document(one.id)).id == single.id
    with pytest.raises(NotFoundError):
        await service.latest_for_document(two.id)
    with pytest.raises(NotFoundError):
        await service.latest_for_document(99999)
