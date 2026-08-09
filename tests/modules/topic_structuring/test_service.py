"""Topic structuring service tests using an in-memory database and mocked model output."""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.topic_structuring.schema import (
    TopicStructuringParseRequest,
    TopicStructuringPatchRequest,
)
from app.modules.topic_structuring.service import TopicStructuringService


async def _pico_extractor(_: str, __: int | None) -> str:
    return json.dumps(
        {
            "structuring_status": "pico",
            "disease": "type 2 diabetes",
            "intervention": "metformin",
            "outcome": "HbA1c",
            "study_type": "randomized trial",
            "clarification_questions": [
                {"question": "Which age group?", "clarifies_field": "target"}
            ],
        }
    )


async def _unstructured_extractor(_: str, __: int | None) -> str:
    return json.dumps(
        {
            "structuring_status": "unstructured",
            "reason": "The topic is a broad conceptual discussion.",
            "focus_points": ["conceptual boundaries"],
            "clarification_questions": [
                {"question": "What is the intended use?", "clarifies_field": "general"}
            ],
        }
    )


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_edit_and_clarification_create_versions(session: AsyncSession) -> None:
    service = TopicStructuringService(session, candidate_extractor=_pico_extractor)
    created = await service.parse(
        TopicStructuringParseRequest(topic="Metformin for diabetes outcomes")
    )

    assert (
        created.candidate.to_search_intent(created.original_topic).disease
        == "type 2 diabetes"
    )
    question_id = created.candidate.clarification_questions[0].id
    answered = await service.patch(
        created.id,
        TopicStructuringPatchRequest(
            clarification_question_id=question_id, answer="adults"
        ),
    )
    edited = await service.patch(
        created.id,
        TopicStructuringPatchRequest(field="outcome", value="change in HbA1c"),
    )

    assert answered.candidate.target == "adults"
    assert answered.candidate.known_fields["target"] is True
    assert edited.current_version == 3
    assert [version.version for version in edited.versions] == [1, 2, 3]
    assert edited.original_topic == "Metformin for diabetes outcomes"


@pytest.mark.asyncio
async def test_unstructured_topic_keeps_topic_without_pico_fields(
    session: AsyncSession,
) -> None:
    service = TopicStructuringService(
        session, candidate_extractor=_unstructured_extractor
    )
    created = await service.parse(
        TopicStructuringParseRequest(topic="Ethical perspectives on precision medicine")
    )

    assert created.candidate.structuring_status == "unstructured"
    assert created.candidate.reason == "The topic is a broad conceptual discussion."
    assert created.candidate.disease is None
    assert created.candidate.focus_points == ["conceptual boundaries"]
