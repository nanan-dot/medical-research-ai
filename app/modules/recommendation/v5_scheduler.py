"""In-process scheduler using a separate database session per run."""

import asyncio
from contextlib import suppress
from typing import ClassVar

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import LLMClientError
from app.integrations.ollama.client import OllamaClient
from app.integrations.pubmed.client import PubMedClient
from app.modules.literature_search.pubmed_executor import PubMedExecutor
from app.modules.recommendation.reason_generator import (
    NarrationLLM,
    RecommendationNarrator,
)
from app.modules.recommendation.v5_repository import RecommendationRepository
from app.modules.recommendation.v5_service import RecommendationV5Service


class RecommendationScheduler:
    _tasks: ClassVar[dict[int, asyncio.Task[None]]] = {}
    _recovery_task: ClassVar[asyncio.Task[None] | None] = None
    _worker_guard: ClassVar[asyncio.Lock | None] = None

    @classmethod
    def schedule(cls, run_id: int) -> None:
        current = cls._tasks.get(run_id)
        if current and not current.done():
            return
        task = asyncio.create_task(cls._run_serialized(run_id))
        cls._tasks[run_id] = task
        task.add_done_callback(lambda _: cls._tasks.pop(run_id, None))

    @classmethod
    def cancel(cls, run_id: int) -> None:
        # 持久化 cancel_requested 是事实来源；不直接取消协程，确保状态能落库。
        return None

    @classmethod
    async def recover(cls) -> None:
        async with AsyncSessionLocal() as session:
            repository = RecommendationRepository(session)
            runs = await repository.list_recoverable()
            try:
                narration_runs = await repository.list_narration_recoverable()
            except AttributeError:
                # Lightweight scheduler test doubles from older callers expose
                # only main-run recovery; production repositories always expose it.
                narration_runs = []
            for run in runs:
                if run.status == "running":
                    run.status = "queued"
                    run.started_at = None
                    run.heartbeat_at = None
            await session.commit()
        for run in [*runs, *narration_runs]:
            cls.schedule(run.id)

    @classmethod
    def start_recovery_loop(cls) -> None:
        if cls._recovery_task is not None and not cls._recovery_task.done():
            return
        cls._recovery_task = asyncio.create_task(cls._recovery_loop())

    @classmethod
    async def stop_recovery_loop(cls) -> None:
        if cls._recovery_task is None:
            return
        cls._recovery_task.cancel()
        with suppress(asyncio.CancelledError):
            await cls._recovery_task
        cls._recovery_task = None

    @classmethod
    async def _recovery_loop(cls) -> None:
        while True:
            await cls.recover()
            await asyncio.sleep(60)

    @classmethod
    async def _run_serialized(cls, run_id: int) -> None:
        """Serialize durable writers so SQLite recovery and new runs cannot lock each other."""
        if cls._worker_guard is None:
            cls._worker_guard = asyncio.Lock()
        async with cls._worker_guard:
            await cls._run(run_id)

    @staticmethod
    async def _run(run_id: int) -> None:
        client = PubMedClient.from_settings()
        llm: NarrationLLM | None = None
        try:
            try:
                llm = (
                    OllamaClient.from_settings()
                    if settings.DEFAULT_MODEL_PROVIDER == "ollama"
                    else LLMClient.from_settings()
                )
            except LLMClientError:
                llm = None
            async with AsyncSessionLocal() as session:
                service = RecommendationV5Service(
                    session, narrator=RecommendationNarrator(llm)
                )
                await service.run(run_id, PubMedExecutor(client))
                await service.polish_run(run_id)
        finally:
            await client.aclose()
            if llm is not None:
                await llm.aclose()
