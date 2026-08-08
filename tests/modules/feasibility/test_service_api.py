"""Service, persistence, versioning, and router tests for feasibility scoring."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.evidence_matrix.model import EvidenceMatrix
from app.modules.feasibility.model import FeasibilityWeightProfile
from app.modules.feasibility.schema import FeasibilityRequest, UserAssessment
from app.modules.feasibility.service import FeasibilityService
from app.modules.research_conditions.model import ResearchConditions
from app.modules.research_direction.model import ResearchDirection


def _direction(
    conditions_id: int,
    matrix_id: int,
    *,
    name: str,
    evidence_count: int,
    methods: str | None,
) -> ResearchDirection:
    return ResearchDirection(
        research_conditions_id=conditions_id,
        evidence_matrix_id=matrix_id,
        name=name,
        question="Question",
        research_object="Population",
        study_type="cohort",
        evidence_json=json.dumps([{"id": index} for index in range(evidence_count)]),
        current_evidence="Current evidence",
        current_evidence_sources_json="[]",
        controversy="Controversy",
        controversy_sources_json="[]",
        gap="Gap",
        novelty_uncertainty="Uncertain",
        priority="medium",
        generation_strategy="gap-based",
        methods=methods,
        generation_metadata_json="{}",
    )


async def _seed_directions(session) -> tuple[ResearchDirection, ResearchDirection]:
    conditions = ResearchConditions(current_version=1)
    matrix = EvidenceMatrix(name="Matrix", description="", status="active", version=1)
    session.add_all([conditions, matrix])
    await session.flush()
    first = _direction(
        conditions.id,
        matrix.id,
        name="Evidence-heavy candidate",
        evidence_count=4,
        methods="Defined method",
    )
    second = _direction(
        conditions.id,
        matrix.id,
        name="Operationally-ready candidate",
        evidence_count=1,
        methods=None,
    )
    session.add_all([first, second])
    await session.flush()
    return first, second


def _assessment(score: float) -> list[UserAssessment]:
    return [
        UserAssessment(
            dimension="sample_availability",
            score=score,
            basis="Verified local sample access.",
        )
    ]


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'feasibility.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_service_persists_default_profile_versions_and_rank_change(session) -> None:
    first, second = await _seed_directions(session)
    service = FeasibilityService(session)

    first_score = await service.score(
        first.id,
        FeasibilityRequest(user_assessments=_assessment(10)),
    )
    await service.score(
        second.id,
        FeasibilityRequest(user_assessments=_assessment(90)),
    )
    reweighted = await service.rescore_with_weights(
        first.id,
        {"sample_availability": 20},
    )

    profile = (await session.execute(select(FeasibilityWeightProfile))).scalar_one()
    versions = await service.versions(first.id)
    first_user_dimension = next(
        dimension
        for dimension in reweighted.dimensions
        if dimension.dimension == "sample_availability"
    )

    assert profile.is_default is True
    assert json.loads(profile.weights_json)["budget"] == 1.0
    assert first_score.version == 1
    assert [version.version for version in versions] == [1, 2]
    assert first_user_dimension.score == 10
    assert reweighted.weights["sample_availability"] == 20
    assert reweighted.ranking_sensitive is True


@pytest.fixture
async def client(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'feasibility_api.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as seed_session:
        first, _ = await _seed_directions(seed_session)
        direction_id = first.id
        await seed_session.commit()

    async def override_session():
        async with factory() as database_session:
            try:
                yield database_session
                await database_session.commit()
            except Exception:
                await database_session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client, direction_id
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_router_creates_score_and_exposes_versions(client) -> None:
    test_client, direction_id = client
    created = test_client.post(
        f"/api/v1/research-directions/{direction_id}/feasibility",
        json={
            "user_assessments": [
                {
                    "dimension": "sample_availability",
                    "score": 70,
                    "basis": "Verified local sample access.",
                }
            ]
        },
    )
    patched = test_client.patch(
        f"/api/v1/research-directions/{direction_id}/feasibility/weights",
        json={"weights": {"sample_availability": 3}},
    )
    versions = test_client.get(f"/api/v1/research-directions/{direction_id}/feasibility/versions")
    rejected = test_client.post(
        f"/api/v1/research-directions/{direction_id}/feasibility",
        json={
            "user_assessments": [
                {
                    "dimension": "literature_base",
                    "score": 70,
                    "basis": "Not permitted.",
                }
            ]
        },
    )

    assert created.status_code == 200
    assert patched.status_code == 200
    assert patched.json()["version"] == 2
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == [1, 2]
    assert rejected.status_code == 422
