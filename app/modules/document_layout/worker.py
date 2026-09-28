"""A1 worker with lease fencing, heartbeats and bounded retry."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_layout.model import DocumentSegmentationRevision
from app.modules.document_layout.service import TASK_TYPE, DocumentLayoutService
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository

_LEASE_SECONDS = 60
_HEARTBEAT_SECONDS = 1.0
_MAX_ATTEMPTS = 3
_RETRYABLE = {"layout_segmentation_failed", "segmentation_conflict"}


class DocumentLayoutWorker:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory
        self._owner = f"layout-{uuid4().hex}"

    async def run_once(self) -> bool:
        async with self._factory() as session:
            task = await TaskRepository(session).claim_next(
                self._owner, _LEASE_SECONDS, TASK_TYPE
            )
            if task is None:
                return False
            task_id, attempts = task.id, task.retry_count
            detail = json.loads(task.detail_json)
            await session.commit()
        try:
            revision_id = detail.get("segmentation_revision_id")
            if not isinstance(revision_id, int):
                raise TypeError("Invalid layout task")
            if attempts > _MAX_ATTEMPTS:
                raise RuntimeError("layout_retry_limit")
            await self._run_owned(task_id, revision_id)
        except Exception as exc:  # noqa: BLE001 -- terminal worker boundary stores safe metadata only.
            code = getattr(exc, "code", "layout_segmentation_failed")
            await self._finish_failure(
                task_id, detail, code, code in _RETRYABLE and attempts < _MAX_ATTEMPTS
            )
        return True

    async def _run_owned(self, task_id: int, revision_id: int) -> None:
        async def execute() -> None:
            async with self._factory() as session:
                await DocumentLayoutService(session).execute(
                    revision_id, task_id, self._owner
                )
                await session.commit()

        work = asyncio.create_task(execute())
        heartbeat = asyncio.create_task(self._heartbeat(task_id))
        try:
            done, _ = await asyncio.wait(
                {work, heartbeat}, return_when=asyncio.FIRST_COMPLETED
            )
            if work in done:
                await work
            else:
                await heartbeat
                raise RuntimeError("layout_lease_lost")
        finally:
            work.cancel()
            heartbeat.cancel()
            await asyncio.gather(work, heartbeat, return_exceptions=True)
        async with self._factory() as session:
            task = await session.get(TaskRecord, task_id)
            if (
                task is None
                or task.status != "running"
                or task.lease_owner != self._owner
            ):
                raise RuntimeError("layout_lease_lost")
            task.status = "succeeded"
            task.phase = "ready"
            task.progress = 100
            task.active_idempotency_key = None
            task.finished_at = datetime.now(UTC)
            task.lease_owner = task.lease_expires_at = None
            await session.commit()

    async def _heartbeat(self, task_id: int) -> None:
        while True:
            await asyncio.sleep(_HEARTBEAT_SECONDS)
            async with self._factory() as session:
                owned = await TaskRepository(session).renew_lease(
                    task_id, self._owner, _LEASE_SECONDS
                )
                await session.commit()
            if not owned:
                return

    async def _finish_failure(
        self, task_id: int, detail: dict[str, object], code: str, retry: bool
    ) -> None:
        async with self._factory() as session:
            task = await session.get(TaskRecord, task_id)
            if task is None or task.status in {"cancelled", "succeeded"}:
                return
            task.status = "queued" if retry else "failed"
            task.phase = "retry_wait" if retry else "failed"
            task.error_code = code
            task.error_message = "PDF layout segmentation did not complete"
            task.finished_at = None if retry else datetime.now(UTC)
            if not retry:
                task.active_idempotency_key = None
            task.lease_owner = task.lease_expires_at = None
            revision_id = detail.get("segmentation_revision_id")
            if isinstance(revision_id, int):
                await session.execute(
                    update(DocumentSegmentationRevision)
                    .where(
                        DocumentSegmentationRevision.id == revision_id,
                        DocumentSegmentationRevision.segmentation_fingerprint.is_(None),
                    )
                    .values(
                        state="pending" if retry else "failed",
                        error_code=code,
                        error_message=task.error_message,
                        finished_at=None if retry else datetime.now(UTC),
                    )
                )
            await session.commit()
