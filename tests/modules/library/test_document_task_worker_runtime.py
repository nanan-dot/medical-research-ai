"""Acceptance coverage for the persistent document-task worker runtime."""

from __future__ import annotations

import asyncio

import pytest

from app.cli import document_task_worker


@pytest.mark.asyncio
async def test_worker_runtime_keeps_polling_until_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-LIB-26: a queued import is not stranded after one worker pass."""

    stop_event = asyncio.Event()
    calls = 0

    class FakeWorker:
        async def run_once(self) -> bool:
            nonlocal calls
            calls += 1
            if calls == 2:
                stop_event.set()
            return calls == 1

    monkeypatch.setattr(document_task_worker, "DocumentTaskWorker", lambda _sessions: FakeWorker())
    await document_task_worker.run_worker(once=False, poll_seconds=0, stop_event=stop_event)

    assert calls == 2


@pytest.mark.asyncio
async def test_worker_runtime_once_mode_claims_exactly_one_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-LIB-27: maintenance mode retains the explicit one-task CLI option."""

    calls = 0

    class FakeWorker:
        async def run_once(self) -> bool:
            nonlocal calls
            calls += 1
            return True

    monkeypatch.setattr(document_task_worker, "DocumentTaskWorker", lambda _sessions: FakeWorker())
    await document_task_worker.run_worker(once=True, poll_seconds=0)

    assert calls == 1
