"""Execute queued document operations from the durable task table."""

import argparse
import asyncio

from app.core.database import AsyncSessionLocal, engine
from app.modules.document.task_worker import DocumentTaskWorker


async def run_worker(
    *, once: bool, poll_seconds: float, stop_event: asyncio.Event | None = None
) -> None:
    """Consume document jobs until stopped so accepted imports cannot stay queued."""

    worker = DocumentTaskWorker(AsyncSessionLocal)
    stopping = stop_event or asyncio.Event()
    try:
        while not stopping.is_set():
            processed = await worker.run_once()
            if once:
                return
            if not processed:
                try:
                    await asyncio.wait_for(stopping.wait(), timeout=poll_seconds)
                except TimeoutError:
                    pass
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process one queued task and exit.")
    parser.add_argument("--poll-seconds", type=float, default=0.5, help="Idle polling interval (default: 0.5).")
    args = parser.parse_args()
    if args.poll_seconds < 0:
        parser.error("--poll-seconds must be non-negative")
    try:
        asyncio.run(run_worker(once=args.once, poll_seconds=args.poll_seconds))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
