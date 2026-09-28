"""离线黄金集验证：Windows 重复运行、阅读器顺序与可选 WSL/Linux 对照。"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings
from app.modules.document_anchor.contract import validate_records
from app.modules.document_anchor.extractor_runner import (
    PdfTextItemExtractor,
)
from app.modules.document_anchor.toolchain import identity


def wsl_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    return "/mnt/" + resolved[0].lower() + resolved[2:]


async def validate(
    path: Path, linux_node: str | None, linux_cli: str | None
) -> dict[str, object]:
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    extractor = PdfTextItemExtractor()
    first = await extractor.extract(path.resolve(), sha, "golden-first")
    second = await extractor.extract(path.resolve(), sha, "golden-second")
    try:
        assert first.page_hashes == second.page_hashes
        output = await asyncio.to_thread(
            subprocess.run,
            [
                "node",
                "tests/modules/document_anchor/reader_items.mjs",
                str(path.resolve()),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=120,
        )
        reader = json.loads(output.stdout)
        assert len(reader) == len(first.pages)
        for page, expected in zip(first.pages, reader, strict=True):
            assert [
                {"text": item.text, "transform": list(item.transform)}
                for item in page.items
            ] == expected
        cross_platform = False
        if linux_node and linux_cli:
            options_path = extractor._write_options_file()
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    [
                        "wsl",
                        "-d",
                        "Ubuntu",
                        "--",
                        linux_node,
                        linux_cli,
                        "extract",
                        "--input",
                        wsl_path(path),
                        "--expected-sha256",
                        sha,
                        "--request-id",
                        "golden-linux",
                        "--options-file",
                        wsl_path(options_path),
                    ],
                    capture_output=True,
                    timeout=180,
                )
                if result.returncode:
                    raise RuntimeError(f"Linux extractor exited {result.returncode}")
                linux = validate_records(
                    [json.loads(line) for line in result.stdout.splitlines()]
                )
                assert linux.page_hashes == first.page_hashes
                cross_platform = True
            finally:
                options_path.unlink(missing_ok=True)
        return {
            "filename": path.name,
            "sha256": sha,
            "pages": len(first.pages),
            "items": sum(len(page.items) for page in first.pages),
            "page_hashes": first.page_hashes,
            "document_hash": first.document_hash,
            "quality_flags": first.quality_flags,
            "repeat_deterministic": True,
            "reader_items_equal": True,
            "windows_linux_equal": cross_platform,
            "elapsed_seconds_including_comparisons": round(
                time.perf_counter() - started, 3
            ),
        }
    finally:
        first.close()
        second.close()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, nargs="+")
    parser.add_argument("--linux-node")
    parser.add_argument("--linux-cli")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    settings.PDF_TEXTITEM_EXTRACTOR_COMMAND = json.dumps(
        ["node", str(root / "tools/pdf_textitem_extractor/dist/cli.js")]
    )
    results = [
        await validate(path, args.linux_node, args.linux_cli) for path in args.pdf
    ]
    report = {"toolchain": identity(), "documents": results}
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documents": len(results),
                "pages": sum(result["pages"] for result in results),
                "windows_linux_equal": all(
                    result["windows_linux_equal"] for result in results
                ),
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
