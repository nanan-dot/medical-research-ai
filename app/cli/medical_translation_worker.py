"""Run queued Phase 1 medical selection translations."""

import argparse
import asyncio

# Standalone workers do not pass through FastAPI's router import graph.  Load
# the canonical registry before creating a session so all FK targets and ORM
# relationships are available when jobs are claimed and published.
import app.core.models  # noqa: F401
from app.core.database import AsyncSessionLocal, engine
from app.modules.medical_translation.prefetch import (
    DocumentTranslationPrefetchScheduler,
)
from app.modules.medical_translation.worker import MedicalTranslationWorker


async def run_worker(*, once: bool, poll_seconds: float) -> None:
    worker = MedicalTranslationWorker(AsyncSessionLocal)
    prefetch = DocumentTranslationPrefetchScheduler(AsyncSessionLocal)
    try:
        while True:
            queued = await prefetch.run_once()
            processed = await worker.run_once()
            if once:
                return
            if not processed and not queued:
                await asyncio.sleep(poll_seconds)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.poll_seconds < 0:
        parser.error("--poll-seconds must not be negative")
    try:
        asyncio.run(run_worker(once=args.once, poll_seconds=args.poll_seconds))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
