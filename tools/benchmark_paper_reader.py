"""受控 38 页 PDF 的 reader 热路径可重复性能基线。"""

from __future__ import annotations

import statistics
import tempfile
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

from app.modules.document_reader.history import decode_cursor, encode_cursor
from app.modules.document_reader.progress import ExposureFact, project_progress

ITERATIONS = 100
PAGE_COUNT = 38
RANGE_BYTES = 65_536


def _measure(operation: Callable[[], object]) -> list[float]:
    timings: list[float] = []
    for _ in range(ITERATIONS):
        started = perf_counter()
        operation()
        timings.append((perf_counter() - started) * 1000)
    return timings


def _summary(timings: list[float]) -> dict[str, float]:
    ordered = sorted(timings)
    return {
        "median_ms": round(statistics.median(ordered), 4),
        "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 4),
        "max_ms": round(max(ordered), 4),
    }


def _read_first_range(pdf_path: Path) -> bytes:
    with pdf_path.open("rb") as stream:
        return stream.read(RANGE_BYTES)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="paper-reader-benchmark-") as directory:
        pdf_path = Path(directory) / "controlled-38-pages.pdf"
        document = canvas.Canvas(str(pdf_path))
        for page in range(1, PAGE_COUNT + 1):
            document.drawString(72, 720, f"Controlled reader benchmark page {page}")
            document.showPage()
        document.save()

        exposures = [ExposureFact(page, 2_500, 0.8, None) for page in range(1, 27)]
        cursor_timestamp = __import__("datetime").datetime.now(__import__("datetime").UTC)
        cursor = encode_cursor(cursor_timestamp, 100)

        results = {
            "environment": {
                "pdf_pages": PAGE_COUNT,
                "pdf_bytes": pdf_path.stat().st_size,
                "iterations": ITERATIONS,
                "range_bytes": RANGE_BYTES,
            },
            "pdf_first_range": _summary(_measure(lambda: _read_first_range(pdf_path))),
            "progress_projection_26_of_38": _summary(_measure(lambda: project_progress(exposures, PAGE_COUNT))),
            "history_cursor_decode": _summary(_measure(lambda: decode_cursor(cursor))),
        }
        print(results)


if __name__ == "__main__":
    main()
