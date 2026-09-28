import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.common.exceptions import ConflictError
from app.modules.conversation.model import Citation
from app.modules.conversation.service import ConversationService
from app.rag.exceptions import GroundedGenerationError
from app.rag.schemas import (
    EvidenceSet,
    GroundedAnswer,
    GroundedCitation,
    RankedEvidence,
)
from tests.modules.qa.test_conversation_service import FakeClient, indexed


class EvidenceProvider:
    def __init__(self, document_id: int, *, domain_document_id="domain-doc", chunk_id="chunk"):
        self.document_id = document_id
        self.domain_document_id = domain_document_id
        self.chunk_id = chunk_id

    async def evidence_for(self, question, document_ids):
        return EvidenceSet(
            evidence=[
                RankedEvidence(
                    document_id=self.domain_document_id,
                    chunk_id=self.chunk_id,
                    source_path="a",
                    text_original="evidence",
                    rank=1,
                )
            ]
        )


class AnswerProvider:
    def __init__(
        self,
        database_document_id,
        *,
        domain_document_id="domain-doc",
        chunk_id="chunk",
        error: Exception | None = None,
    ):
        self.database_document_id = database_document_id
        self.domain_document_id = domain_document_id
        self.chunk_id = chunk_id
        self.error = error

    async def answer(self, evidence):
        if self.error is not None:
            raise self.error
        return GroundedAnswer(
            answer="grounded",
            citations=[
                GroundedCitation(
                    citation_id=self.chunk_id,
                    document_id=self.domain_document_id,
                    database_document_id=self.database_document_id,
                    chunk_id=self.chunk_id,
                    source_path="a",
                )
            ],
        )


@pytest.mark.asyncio
async def test_wp7_grounded_persists_authorized_citation(session, tmp_path):
    document = await indexed(session, tmp_path, "one")
    service = ConversationService(session, client_factory=FakeClient, grounded_mode="grounded", evidence_provider=EvidenceProvider(document.id), grounded_answer_provider=AnswerProvider(document.id))
    conversation = await service.create([document.id])
    answer = await service.ask(conversation.id, "Question")
    assert answer.content == "grounded" and answer.citations[0].evidence_type == "grounded"
    assert [item.role for item in (await service.get(conversation.id)).messages] == [
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_wp7_grounded_rejects_missing_database_identity(session, tmp_path):
    document = await indexed(session, tmp_path, "one")
    service = ConversationService(session, grounded_mode="grounded", evidence_provider=EvidenceProvider(document.id), grounded_answer_provider=AnswerProvider(None))
    conversation = await service.create([document.id])
    with pytest.raises(ConflictError): await service.ask(conversation.id, "Question")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("evidence_domain_id", "evidence_chunk_id", "citation_domain_id", "citation_chunk_id", "database_document_id"),
    [
        ("domain-doc", "chunk", "domain-doc", "chunk", 999999),
        ("domain-doc", "chunk", "123", "chunk", None),
        ("domain-doc", "chunk", "domain-doc", "unknown-chunk", 1),
        ("domain-doc", "chunk", "different-domain", "chunk", 1),
    ],
)
async def test_wp7_grounded_rejects_invalid_citation_identity(
    session,
    tmp_path,
    evidence_domain_id,
    evidence_chunk_id,
    citation_domain_id,
    citation_chunk_id,
    database_document_id,
):
    document = await indexed(session, tmp_path, "one")
    if database_document_id == 1:
        database_document_id = document.id
    service = ConversationService(
        session,
        grounded_mode="grounded",
        evidence_provider=EvidenceProvider(
            document.id,
            domain_document_id=evidence_domain_id,
            chunk_id=evidence_chunk_id,
        ),
        grounded_answer_provider=AnswerProvider(
            database_document_id,
            domain_document_id=citation_domain_id,
            chunk_id=citation_chunk_id,
        ),
    )
    conversation = await service.create([document.id])
    with pytest.raises(ConflictError):
        await service.ask(conversation.id, "Question")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "expected_status"),
    [
        (None, "unavailable"),
        (AnswerProvider(1), "completed"),
        (AnswerProvider(1, error=GroundedGenerationError("failed")), "failed"),
        (AnswerProvider(1, error=ConflictError("failed")), "failed"),
    ],
)
async def test_wp7_shadow_isolated_from_paperqa_result(
    session, tmp_path, provider, expected_status
):
    document = await indexed(session, tmp_path, "one")
    statuses: list[str] = []
    service = ConversationService(
        session,
        client_factory=FakeClient,
        grounded_mode="shadow",
        evidence_provider=EvidenceProvider(document.id) if provider is not None else None,
        grounded_answer_provider=provider,
        shadow_status_callback=statuses.append,
    )
    conversation = await service.create([document.id])
    answer = await service.ask(conversation.id, "Question")
    restored = await service.get(conversation.id)
    assert answer.content == "Answer from idx-one"
    assert [message.role for message in restored.messages] == ["user", "assistant"]
    assert restored.messages[1].citations[0].evidence_type == "paperqa"
    assert statuses == [expected_status]


@pytest.mark.asyncio
async def test_wp7_grounded_rollback_on_citation_save_failure(session, tmp_path, monkeypatch):
    document = await indexed(session, tmp_path, "one")
    service = ConversationService(
        session,
        grounded_mode="grounded",
        evidence_provider=EvidenceProvider(document.id),
        grounded_answer_provider=AnswerProvider(document.id),
    )
    conversation = await service.create([document.id])
    original_create = service.repo.create

    async def fail_citation(entity):
        if isinstance(entity, Citation):
            raise SQLAlchemyError("citation write failed")
        return await original_create(entity)

    monkeypatch.setattr(service.repo, "create", fail_citation)
    with pytest.raises(ConflictError, match="could not be saved"):
        await service.ask(conversation.id, "Question")
    restored = await service.get(conversation.id)
    assert restored.messages == []
