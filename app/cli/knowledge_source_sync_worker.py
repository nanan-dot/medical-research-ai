"""Executable process for durable knowledge-source synchronization tasks."""

import argparse
import asyncio
import logging
import signal

from app.core.database import AsyncSessionLocal, engine
from app.modules.knowledge_source.sync_task_service import KnowledgeSourceSyncWorker


def build_parser() -> argparse.ArgumentParser:
    """Build the worker CLI argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one available task and exit.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=2.0,
        help="Idle polling interval for continuous mode.",
    )
    return parser


async def run_worker(*, once: bool, poll_seconds: float) -> None:
    """Run one task or a supervised polling loop, then release DB resources."""
    worker = KnowledgeSourceSyncWorker(AsyncSessionLocal)
    try:
        if once:
            await worker.run_once()
            return
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(signal_name, stop_event.set)
            except NotImplementedError:
                signal.signal(
                    signal_name,
                    lambda *_args: loop.call_soon_threadsafe(stop_event.set),
                )
        await worker.run(stop_event, poll_seconds=poll_seconds)
    finally:
        await engine.dispose()


def main() -> int:
    """Parse CLI arguments and start the asynchronous worker runtime."""
    args = build_parser().parse_args()
    if args.poll_seconds < 0:
        raise SystemExit("--poll-seconds must be non-negative")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker(once=args.once, poll_seconds=args.poll_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
