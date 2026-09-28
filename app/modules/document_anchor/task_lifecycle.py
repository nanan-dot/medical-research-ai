"""统一任务 API 的 A0 领域同步；条件更新与发布互斥。"""

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.task.model import TaskRecord


async def cancel_anchor_task(session: AsyncSession, task: TaskRecord) -> TaskRecord:
    """Cancel queued/running work atomically and hide unfinished domain output."""
    if task.phase == "publishing":
        raise ConflictError("Anchor extraction can no longer be cancelled while publishing")
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
        raise ConflictError("Only active anchor tasks can be cancelled")
    revision_id = json.loads(task.detail_json).get("revision_id")
    await session.execute(
        update(DocumentAnchorRevision)
        .where(
            DocumentAnchorRevision.id == revision_id,
            DocumentAnchorRevision.extraction_fingerprint.is_(None),
        )
        .values(state="cancelled", finished_at=datetime.now(UTC))
    )
    await session.refresh(task)
    return task


async def retry_anchor_task(session: AsyncSession, task: TaskRecord) -> TaskRecord:
    """Explicit retry starts a new bounded attempt budget after configuration repair."""
    # 不可恢复的文件/策略错误必须创建新版本或显式调整策略，不能无效循环。
    if task.error_code in {
        "invalid_pdf",
        "encrypted_pdf",
        "file_hash_mismatch",
        "resource_limit_exceeded",
        "invalid_argument",
    }:
        raise ConflictError(
            "This extraction requires a readable PDF or an approved configuration change"
        )
    active = await session.scalar(
        select(TaskRecord.id).where(
            TaskRecord.id != task.id,
            TaskRecord.active_idempotency_key == task.idempotency_key,
        )
    )
    if active is not None:
        raise ConflictError("Another extraction task is already active")
    result = await session.execute(
        update(TaskRecord)
        .where(TaskRecord.id == task.id, TaskRecord.status == "failed")
        .values(
            status="queued",
            active_idempotency_key=task.idempotency_key,
            progress=0,
            completed_units=0,
            total_units=None,
            current_item=None,
            phase="queued",
            retry_count=0,
            error_code=None,
            error_message=None,
            finished_at=None,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    if getattr(result, "rowcount", 0) != 1:
        raise ConflictError("Only failed anchor tasks can be retried")
    revision_id = json.loads(task.detail_json).get("revision_id")
    await session.execute(
        update(DocumentAnchorRevision)
        .where(
            DocumentAnchorRevision.id == revision_id,
            DocumentAnchorRevision.extraction_fingerprint.is_(None),
        )
        .values(state="pending", finished_at=None, error_code=None, error_message=None)
    )
    await session.refresh(task)
    return task
