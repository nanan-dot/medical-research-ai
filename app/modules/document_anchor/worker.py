"""统一任务中心的 A0 worker：心跳、取消、租约 fencing 与有限重试。"""

import asyncio
import json
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.extractor_runner import (
    ExtractorExecutionError,
    PdfTextItemExtractor,
)
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_anchor.service import (
    TASK_TYPE,
    AnchorLeaseLostError,
    DocumentAnchorService,
)
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository

_LEASE_SECONDS = 60
_HEARTBEAT_SECONDS = 1.0
_MAX_ATTEMPTS = 3
_RETRYABLE = {
    "anchor_extraction_timeout",
    "anchor_extraction_idle_timeout",
    "anchor_process_failed",
    "anchor_invalid_contract",
    "extraction_failed",
    "contract_write_failed",
}


class DocumentAnchorWorker:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self._worker_id = f"anchor-{uuid4().hex}"

    async def run_once(self) -> bool:
        async with self._session_factory() as session:
            task = await TaskRepository(session).claim_next(
                self._worker_id, _LEASE_SECONDS, TASK_TYPE
            )
            if task is None:
                return False
            task_id, attempts = task.id, task.retry_count
            detail = task.detail_json
            await session.commit()
        try:
            revision_id = json.loads(detail).get("revision_id")
            if not isinstance(revision_id, int):
                raise TypeError("Invalid anchor task")
            if attempts > _MAX_ATTEMPTS:
                raise ExtractorExecutionError("anchor_retry_limit")
            await self._run_owned(task_id, revision_id)
        except asyncio.CancelledError:
            await self._finish_failure(task_id, "anchor_worker_interrupted", False)
            raise
        except Exception as exc:  # noqa: BLE001 -- worker 边界统一安全错误并持久化失败，不泄漏正文。
            code = getattr(exc, "code", "anchor_extraction_failed")
            retry = code in _RETRYABLE and attempts < _MAX_ATTEMPTS
            if retry:
                await asyncio.sleep(2 ** (attempts - 1))
            await self._finish_failure(task_id, code, retry)
        return True

    async def _run_owned(self, task_id: int, revision_id: int) -> None:
        async def progress(completed: int, total: int) -> None:
            async with self._session_factory() as session:
                if not await TaskRepository(session).renew_lease(
                    task_id, self._worker_id, _LEASE_SECONDS
                ):
                    raise AnchorLeaseLostError("Anchor task cancelled or reclaimed")
                await session.execute(
                    update(TaskRecord)
                    .where(TaskRecord.id == task_id)
                    .values(
                        progress=min(95, int(completed / total * 95)),
                        phase="extracting",
                        completed_units=completed,
                        total_units=total,
                        current_item=f"第 {completed} 页",
                        progress_updated_at=datetime.now(UTC),
                    )
                )
                await session.commit()

        async def execute() -> None:
            async with self._session_factory() as session:
                await DocumentAnchorService(session).execute(
                    revision_id,
                    PdfTextItemExtractor(progress),
                    task_id,
                    self._worker_id,
                )

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
                raise AnchorLeaseLostError("Anchor task cancelled or reclaimed")
        finally:
            work.cancel()
            heartbeat.cancel()
            await asyncio.gather(work, heartbeat, return_exceptions=True)
    async def _heartbeat(self, task_id: int) -> None:
        while True:
            await asyncio.sleep(_HEARTBEAT_SECONDS)
            async with self._session_factory() as session:
                owned = await TaskRepository(session).renew_lease(
                    task_id, self._worker_id, _LEASE_SECONDS
                )
                await session.commit()
                if not owned:
                    return

    async def _finish_failure(self, task_id: int, code: str, retry: bool) -> None:
        async with self._session_factory() as session:
            # 先拿写锁，再判断所有权；取消请求与发布在同一 Task 行上串行。
            result = await session.execute(
                update(TaskRecord)
                .where(
                    TaskRecord.id == task_id,
                    TaskRecord.status == "running",
                    TaskRecord.lease_owner == self._worker_id,
                )
                .values(phase="retry_wait" if retry else "failed")
            )
            task = await session.get(TaskRecord, task_id)
            if task is None:
                return
            owned = getattr(result, "rowcount", 0) == 1
            if not owned and task.status != "cancelled":
                return
            revision_id = None
            with suppress(ValueError, TypeError):
                revision_id = json.loads(task.detail_json).get("revision_id")
            newer = await session.scalar(
                select(TaskRecord.id)
                .where(
                    TaskRecord.id != task_id,
                    TaskRecord.idempotency_key == task.idempotency_key,
                    TaskRecord.status.in_(("queued", "running")),
                )
                .limit(1)
            )
            if isinstance(revision_id, int) and newer is None:
                state = (
                    "cancelled"
                    if task.status == "cancelled"
                    else "pending"
                    if retry
                    else "failed"
                )
                await session.execute(
                    update(DocumentAnchorRevision)
                    .where(
                        DocumentAnchorRevision.id == revision_id,
                        DocumentAnchorRevision.extraction_fingerprint.is_(None),
                    )
                    .values(
                        state=state,
                        error_code=code,
                        error_message="PDF TextItem extraction did not complete",
                        finished_at=None if retry else datetime.now(UTC),
                    )
                )
            if owned:
                task.status = "queued" if retry else "failed"
                task.error_code = code
                task.error_message = "PDF TextItem extraction did not complete"
                task.finished_at = None if retry else datetime.now(UTC)
                if not retry:
                    task.active_idempotency_key = None
                task.lease_owner = task.lease_expires_at = None
            await session.commit()
