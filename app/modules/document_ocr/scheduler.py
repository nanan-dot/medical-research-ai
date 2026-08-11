"""OCR 后台任务调度器。"""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.modules.document_ocr.service import DocumentOcrRunner


class OcrTaskScheduler:
    """进程内调度只负责启动独立会话 runner，状态始终落库而非伪造进度。"""

    # 进程内任务注册表：类级共享状态，惰性初始化避免可变默认值共享陷阱。
    _tasks: dict[int, asyncio.Task[None]] | None = None

    @classmethod
    def _registry(cls) -> dict[int, asyncio.Task[None]]:
        if cls._tasks is None:
            cls._tasks = {}
        return cls._tasks

    @classmethod
    def schedule(cls, job_id: int) -> None:
        tasks = cls._registry()
        if job_id in tasks and not tasks[job_id].done():
            return
        task = asyncio.create_task(cls._run(job_id))
        tasks[job_id] = task
        task.add_done_callback(lambda _: tasks.pop(job_id, None))

    @classmethod
    def cancel(cls, job_id: int) -> None:
        task = cls._registry().get(job_id)
        if task is not None:
            task.cancel()

    @staticmethod
    async def _run(job_id: int) -> None:
        async with AsyncSessionLocal() as session:
            await DocumentOcrRunner(session).run(job_id)
