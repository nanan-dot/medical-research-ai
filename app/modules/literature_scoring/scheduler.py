"""In-process scheduler for durable literature scoring generations."""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionLocal
from app.modules.literature_scoring.service import LiteratureScoringService


class LiteratureScoringScheduler:
    """Tasks have separate sessions; cancellation state remains in the database."""

    _tasks: dict[int, asyncio.Task[None]] | None = None

    @classmethod
    def _registry(cls) -> dict[int, asyncio.Task[None]]:
        if cls._tasks is None:
            cls._tasks = {}
        return cls._tasks

    @classmethod
    def schedule(cls, generation_id: int) -> None:
        tasks = cls._registry()
        if generation_id in tasks and not tasks[generation_id].done():
            return
        task = asyncio.create_task(cls._run(generation_id))
        tasks[generation_id] = task
        task.add_done_callback(lambda _: tasks.pop(generation_id, None))

    @classmethod
    def cancel(cls, generation_id: int) -> None:
        task = cls._registry().get(generation_id)
        if task is not None:
            task.cancel()

    @staticmethod
    async def _run(generation_id: int) -> None:
        async with AsyncSessionLocal() as session:
            await LiteratureScoringService(session).run_queued_generation(generation_id)
