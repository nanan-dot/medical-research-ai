"""OCR 文本输出的受控落盘。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings
from app.modules.document_ocr.model import DocumentOcrPage


def persist_ocr_output(job_id: int, pages: list[DocumentOcrPage]) -> tuple[str, str]:
    """先在 OCR 专属目录写入临时文件，再原子替换，避免生成半成品输出。"""

    root = settings.OCR_OUTPUT_DIR.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    job_directory = _safe_descendant(resolved_root, resolved_root / f"job-{job_id}")
    job_directory.mkdir(exist_ok=True)
    target = _safe_descendant(resolved_root, job_directory / "ocr.txt")
    temporary = _safe_descendant(resolved_root, job_directory / "ocr.txt.tmp")
    output = "\n\n".join(
        f"[Page {page.page_number}]\n{page.text or ''}" for page in pages if page.text
    )
    try:
        temporary.write_text(output, encoding="utf-8")
        temporary.replace(target)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise
    relative_path = target.relative_to(resolved_root).as_posix()
    return relative_path, hashlib.sha256(output.encode("utf-8")).hexdigest()


def _safe_descendant(root: Path, candidate: Path) -> Path:
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(root)
    except ValueError as exc:
        raise OSError("OCR output path escapes its configured root") from exc
    return resolved_candidate
