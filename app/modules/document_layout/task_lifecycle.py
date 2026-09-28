"""Task-center cancellation/retry transitions for unpublished A1 revisions."""

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.modules.document_layout.model import DocumentSegmentationRevision
from app.modules.task.model import TaskRecord


async def cancel_layout_task(session: AsyncSession, task: TaskRecord) -> TaskRecord:
    if task.phase == "publishing":
        raise ConflictError(
            "Layout segmentation can no longer be cancelled while publishing"
        )
    result = await session.execute(
        update(TaskRecord)
        .where(
            TaskRecord.id == task.id,
            TaskRecord.status.in_(("pending", "queued", "running")),
        )
        .values(
            status="cancelled",
            active_idempotency_key=None,
            lease_owner=None,
            lease_expires_at=None,
            phase="cancelled",
            finished_at=datetime.now(UTC),
        )
    )
    if getattr(result, "rowcount", 0) != 1:
        raise ConflictError("Only active layout tasks can be cancelled")
    revision_id = json.loads(task.detail_json).get("segmentation_revision_id")
    await session.execute(
        update(DocumentSegmentationRevision)
        .where(
            DocumentSegmentationRevision.id == revision_id,
            DocumentSegmentationRevision.segmentation_fingerprint.is_(None),
        )
        .values(state="cancelled", finished_at=datetime.now(UTC))
    )
    await session.refresh(task)
    return task


async def retry_layout_task(session: AsyncSession, task: TaskRecord) -> TaskRecord:
    if task.status != "failed":
        raise ConflictError("Only failed layout tasks can be retried")
    active = await session.scalar(
        select(TaskRecord.id).where(
            TaskRecord.id != task.id,
            TaskRecord.active_idempotency_key == task.idempotency_key,
        )
    )
    if active is not None:
        raise ConflictError("Another layout segmentation task is already active")
    result = await session.execute(
        update(TaskRecord)
        .where(TaskRecord.id == task.id, TaskRecord.status == "failed")
        .values(
            status="queued",
            active_idempotency_key=task.idempotency_key,
            progress=0,
            phase="queued",
            error_code=None,
            error_message=None,
            finished_at=None,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    if getattr(result, "rowcount", 0) != 1:
        raise ConflictError("Only failed layout tasks can be retried")
    revision_id = json.loads(task.detail_json).get("segmentation_revision_id")
    await session.execute(
        update(DocumentSegmentationRevision)
        .where(
            DocumentSegmentationRevision.id == revision_id,
            DocumentSegmentationRevision.segmentation_fingerprint.is_(None),
        )
        .values(state="pending", error_code=None, error_message=None, finished_at=None)
    )
    await session.refresh(task)
    return task
