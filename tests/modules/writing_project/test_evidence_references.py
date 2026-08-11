from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError, NotFoundError
from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.conversation.model import Citation, Conversation, Message
from app.modules.research_context.schema import ResearchContextCreate
from app.modules.research_context.service import ResearchContextService
from app.modules.writing_project.schema import (
    ContentSegment,
    GeneratedContent,
    WritingEvidenceReferenceCreate,
    WritingProjectCreate,
    WritingProjectUpdate,
)
from app.modules.writing_project.service import WritingProjectService
from tests.modules.document.conftest import create_document


@pytest.fixture
async def service(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'evidence.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield WritingProjectService(session), session
    await engine.dispose()


def content_with_segment() -> GeneratedContent:
    return GeneratedContent(
        segments=[ContentSegment(id="segment-1", text="Claim", origin="user_provided")]
    )


@pytest.mark.asyncio
async def test_writing_evidence_reference_reads_back_honest_missing_locations(
    service, tmp_path: Path
) -> None:
    writing_service, session = service
    document, _ = await create_document(session, tmp_path / "paper.pdf", "paper.pdf")
    project = await writing_service.create(
        WritingProjectCreate(
            name="Review", writing_type="review", generated_content=content_with_segment()
        )
    )

    reference = await writing_service.add_evidence_reference(
        project.id,
        WritingEvidenceReferenceCreate(
            segment_id="segment-1", source_type="document", document_id=document.id
        ),
    )

    assert reference.document_id == document.id
    assert reference.page is None
    assert reference.section is None
    assert reference.evidence_text is None
    assert (await writing_service.get(project.id)).evidence_references == [reference]


@pytest.mark.asyncio
async def test_writing_reference_can_copy_a_real_conversation_citation_and_survives_snapshot(
    service, tmp_path: Path
) -> None:
    writing_service, session = service
    document, _ = await create_document(session, tmp_path / "paper.pdf", "paper.pdf")
    now = datetime.now(UTC)
    conversation = Conversation(
        document_ids=f"[{document.id}]", title=None, created_at=now, updated_at=now
    )
    session.add(conversation)
    await session.flush()
    message = Message(
        conversation_id=conversation.id,
        sequence=1,
        role="assistant",
        content="answer",
        created_at=now,
    )
    session.add(message)
    await session.flush()
    citation = Citation(
        message_id=message.id,
        document_id=document.id,
        evidence_type="paperqa",
        page=7,
        section="Results",
        evidence_text="Observed effect.",
        citation_text="Local paper",
        retrieval_score=0.9,
    )
    session.add(citation)
    await session.flush()
    project = await writing_service.create(
        WritingProjectCreate(
            name="Review", writing_type="review", generated_content=content_with_segment()
        )
    )

    reference = await writing_service.add_evidence_reference(
        project.id,
        WritingEvidenceReferenceCreate(
            segment_id="segment-1",
            source_type="conversation_citation",
            conversation_citation_id=citation.id,
        ),
    )
    snapshot = await writing_service.save_version(project.id, expected_version=1)
    restored = await writing_service.restore_version(
        project.id, snapshot.version, expected_version=1
    )

    assert reference.page == 7
    assert reference.section == "Results"
    assert restored.evidence_references[0].citation_text == "Local paper"
    assert restored.generated_content.segments[0].id == "segment-1"


@pytest.mark.asyncio
async def test_writing_reference_rejects_unknown_document(service) -> None:
    writing_service, _ = service
    project = await writing_service.create(
        WritingProjectCreate(
            name="Review", writing_type="review", generated_content=content_with_segment()
        )
    )

    with pytest.raises(NotFoundError, match="Document not found"):
        await writing_service.add_evidence_reference(
            project.id,
            WritingEvidenceReferenceCreate(
                segment_id="segment-1", source_type="document", document_id=999
            ),
        )


@pytest.mark.asyncio
async def test_writing_reference_rejects_unknown_content_segment(
    service, tmp_path: Path
) -> None:
    writing_service, session = service
    document, _ = await create_document(session, tmp_path / "paper.pdf", "paper.pdf")
    project = await writing_service.create(
        WritingProjectCreate(
            name="Review", writing_type="review", generated_content=content_with_segment()
        )
    )

    with pytest.raises(ConflictError, match="Content segment not found"):
        await writing_service.add_evidence_reference(
            project.id,
            WritingEvidenceReferenceCreate(
                segment_id="segment-absent",
                source_type="document",
                document_id=document.id,
            ),
        )


@pytest.mark.asyncio
async def test_context_assignment_rejects_existing_evidence_outside_context(
    service, tmp_path: Path
) -> None:
    writing_service, session = service
    document, _ = await create_document(session, tmp_path / "paper.pdf", "paper.pdf")
    project = await writing_service.create(
        WritingProjectCreate(
            name="Review", writing_type="review", generated_content=content_with_segment()
        )
    )
    await writing_service.add_evidence_reference(
        project.id,
        WritingEvidenceReferenceCreate(
            segment_id="segment-1", source_type="document", document_id=document.id
        ),
    )
    context = await ResearchContextService(session).create(
        ResearchContextCreate(name="Empty scope")
    )

    with pytest.raises(ConflictError, match="not linked"):
        await writing_service.update(
            project.id,
            WritingProjectUpdate(
                research_context_id=context.id,
                expected_version=project.version,
            ),
        )
