"""OCR 后台任务调度器。"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.modules.document_ocr.service import DocumentOcrRunner


class OcrTaskScheduler:
    """进程内调度只负责启动独立会话 runner，状态始终落库而非伪造进度。"""

    _tasks: dict[int, asyncio.Task[None]] = {}

    @classmethod
    def schedule(cls, job_id: int) -> None:
        if job_id in cls._tasks and not cls._tasks[job_id].done():
            return
        task = asyncio.create_task(cls._run(job_id))
        cls._tasks[job_id] = task
        task.add_done_callback(lambda _: cls._tasks.pop(job_id, None))

    @classmethod
    def cancel(cls, job_id: int) -> None:
        task = cls._tasks.get(job_id)
        if task is not None:
            task.cancel()

    @staticmethod
    async def _run(job_id: int) -> None:
        async with AsyncSessionLocal() as session:
            await DocumentOcrRunner(session).run(job_id)
