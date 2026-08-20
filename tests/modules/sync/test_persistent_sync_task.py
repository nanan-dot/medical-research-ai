"""Acceptance tests for durable, idempotent knowledge-source synchronization."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.knowledge_source.sync_task_service import KnowledgeSourceSyncWorker
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository
from app.modules.task.schema import TaskStatus
from tests.modules.knowledge_source.test_api import create_source


def test_sync_submission_is_accepted_and_idempotent(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-13: repeated submissions return one persistent queued command."""
    root = tmp_path / "source"
    root.mkdir()
    source_id = create_source(client, root).json()["id"]
    first = client.post(f"/api/v1/knowledge-sources/{source_id}/sync")
    second = client.post(f"/api/v1/knowledge-sources/{source_id}/sync")
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["task_id"] == second.json()["task_id"]
    assert first.json()["status"] == "queued"
    assert first.json()["status_url"].endswith(str(first.json()["task_id"]))


@pytest.mark.asyncio
async def test_expired_running_task_is_claimable_again(tmp_path: Path) -> None:
    """AC-14: an abandoned lease does not leave sync work permanently running."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'tasks.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        task = TaskRecord(
            task_type="knowledge_source_sync",
            title="sync",
            status="running",
            progress=10,
            detail_json="{}",
            idempotency_key="sync:1",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        await TaskRepository(session).create(task)
        await session.commit()
    async with factory() as session:
        claimed = await TaskRepository(session).claim_next("worker-a", 60)
        assert claimed is not None
        assert claimed.status == TaskStatus.RUNNING.value
        assert claimed.lease_owner == "worker-a"
        assert claimed.retry_count == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_active_worker_can_renew_its_lease(tmp_path: Path) -> None:
    """AC-14: a live worker heartbeat prevents premature task recovery."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'heartbeat.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        task = TaskRecord(
            task_type="knowledge_source_sync",
            title="sync",
            status=TaskStatus.RUNNING.value,
            progress=10,
            detail_json="{}",
            lease_owner="worker-a",
            lease_expires_at=datetime.now(UTC) + timedelta(seconds=1),
        )
        await TaskRepository(session).create(task)
        await session.commit()
        task_id = task.id
    async with factory() as session:
        renewed = await TaskRepository(session).renew_lease(task_id, "worker-a", 60)
        rejected = await TaskRepository(session).renew_lease(task_id, "worker-b", 60)
        await session.commit()
        assert renewed is True
        assert rejected is False
        stored = await TaskRepository(session).get(task_id)
        assert stored is not None
        assert stored.heartbeat_at is not None
        assert stored.lease_expires_at is not None
        lease_expires_at = stored.lease_expires_at.replace(tzinfo=UTC)
        assert lease_expires_at > datetime.now(UTC) + timedelta(seconds=50)
    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_poll_loop_stops_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """The executable worker keeps polling and honors supervised shutdown."""
    worker = KnowledgeSourceSyncWorker(None)  # type: ignore[arg-type]
    stop_event = asyncio.Event()
    calls = 0

    async def fake_run_once() -> bool:
        nonlocal calls
        calls += 1
        if calls == 2:
            stop_event.set()
        return False

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    await worker.run(stop_event, poll_seconds=0)
    assert calls == 2
