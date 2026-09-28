"""Run queued A0 document-anchor extraction tasks outside HTTP requests."""

import argparse
import asyncio

from app.core.database import AsyncSessionLocal, engine
from app.modules.document_anchor.worker import DocumentAnchorWorker


async def run_worker(*, once: bool, poll_seconds: float) -> None:
    """Process durable A0 work until interrupted or one task is consumed."""
    worker = DocumentAnchorWorker(AsyncSessionLocal)
    try:
        while True:
            processed = await worker.run_once()
            if once:
                return
            if not processed:
                await asyncio.sleep(poll_seconds)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    arguments = parser.parse_args()
    if arguments.poll_seconds < 0:
        parser.error("--poll-seconds must not be negative")
    try:
        asyncio.run(
            run_worker(once=arguments.once, poll_seconds=arguments.poll_seconds)
        )
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
