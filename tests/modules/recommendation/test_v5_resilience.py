"""Temporal and failure-path acceptance tests for recommendation workers."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.core.models  # noqa: F401 - register every foreign-key target for test DDL
from app.core.database import Base
from app.modules.recommendation.v5_errors import classify_run_error
from app.modules.recommendation.v5_repository import RecommendationRepository
from app.modules.recommendation.v5_scheduler import RecommendationScheduler


def test_failure_source_is_not_always_labeled_pubmed() -> None:
    assert classify_run_error(ValueError("bad json"), stage="input_decode") == {
        "code": "recommendation_input_invalid",
        "message": "bad json",
        "provider": None,
    }
    assert classify_run_error(RuntimeError("offline"), stage="pubmed_collection")[
        "provider"
    ] == "pubmed"


@pytest.mark.asyncio
async def test_startup_recovery_requeues_queued_and_reclaims_running(monkeypatch) -> None:
    queued = SimpleNamespace(id=1, status="queued", last_error=None)
    running = SimpleNamespace(id=2, status="running", last_error=None)
    fake_session = SimpleNamespace(commit=AsyncMock())

    class SessionContext:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(
        "app.modules.recommendation.v5_scheduler.AsyncSessionLocal",
        lambda: SessionContext(),
    )
    monkeypatch.setattr(
        "app.modules.recommendation.v5_scheduler.RecommendationRepository.list_recoverable",
        AsyncMock(return_value=[queued, running]),
    )
    scheduled: list[int] = []
    monkeypatch.setattr(RecommendationScheduler, "schedule", scheduled.append)
    await RecommendationScheduler.recover()
    assert running.status == "queued"
    assert scheduled == [1, 2]
    assert fake_session.commit.await_count == 1


@pytest.mark.asyncio
async def test_bounded_async_map_enforces_concurrency_limit() -> None:
    from app.modules.recommendation.external_work import bounded_async_map

    active = 0
    maximum = 0

    async def work(value: int) -> int:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return value

    assert await bounded_async_map(range(20), work, limit=4) == list(range(20))
    assert maximum <= 4


@pytest.mark.asyncio
async def test_scheduler_serializes_recovery_and_new_run_writers(monkeypatch) -> None:
    active = 0
    maximum = 0

    async def fake_run(_run_id: int) -> None:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1

    RecommendationScheduler._worker_guard = None
    monkeypatch.setattr(RecommendationScheduler, "_run", fake_run)
    await asyncio.gather(
        RecommendationScheduler._run_serialized(1),
        RecommendationScheduler._run_serialized(2),
    )
    assert maximum == 1


@pytest.mark.asyncio
async def test_narration_lease_allows_one_claim_and_caches_terminal_fallback(tmp_path) -> None:
    """Independent workers must not invoke a model twice for one fact packet."""
    database_path = tmp_path / "narration-lease.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as first, sessions() as second:
        first_repo = RecommendationRepository(first)
        second_repo = RecommendationRepository(second)
        action, _ = await first_repo.acquire_narration_lease(
            "packet-v1", "first", stale_after=timedelta(minutes=1)
        )
        assert action == "claimed"
        await first.commit()

        action, _ = await second_repo.acquire_narration_lease(
            "packet-v1", "second", stale_after=timedelta(minutes=1)
        )
        assert action == "busy"
        await second.rollback()

        assert await first_repo.finalize_narration_lease(
            fingerprint="packet-v1",
            claim_token="first",
            status="fallback_timeout",
            polished_reason_json=None,
            narration_model=None,
            error_code="narration_timeout",
        )
        await first.commit()
        action, lease = await second_repo.acquire_narration_lease(
            "packet-v1", "second", stale_after=timedelta(minutes=1)
        )
        assert action == "cached"
        assert lease is not None and lease.status == "fallback_timeout"
    await engine.dispose()
