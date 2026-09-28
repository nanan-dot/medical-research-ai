"""Run one durable knowledge-source auto-sync scheduling pass."""

import asyncio

from app.core.database import AsyncSessionLocal, engine
from app.modules.knowledge_source.auto_sync_scheduler import (
    KnowledgeSourceAutoSyncScheduler,
)


async def run_once() -> int:
    """投递到期任务并返回数量；由外部调度器按周期执行此进程。"""
    try:
        async with AsyncSessionLocal() as session:
            source_ids = await KnowledgeSourceAutoSyncScheduler(session).enqueue_due_sources()
            await session.commit()
            return len(source_ids)
    finally:
        await engine.dispose()


def main() -> int:
    """运行一个调度批次。"""
    asyncio.run(run_once())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
