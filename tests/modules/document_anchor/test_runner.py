"""真实子进程的字节限额、失败协议、取消和进程树回收。"""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import psutil
import pytest
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.modules.document_anchor.extractor_runner import (
    ExtractorExecutionError,
    ExtractorUnavailableError,
    PdfTextItemExtractor,
)


def configure(monkeypatch, tmp_path, mode):
    path = tmp_path / "input with spaces.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(30, 50, "test")
    pdf.save()
    monkeypatch.setattr(
        settings,
        "PDF_TEXTITEM_EXTRACTOR_COMMAND",
        json.dumps(
            [
                sys.executable,
                str(Path(__file__).with_name("fake_extractor.py")),
                "--mode",
                mode,
            ]
        ),
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "mode", ["missing_trailer", "wrong_header", "incomplete", "huge"]
)
async def test_exit_zero_cannot_publish_invalid_protocol(monkeypatch, tmp_path, mode):
    path, file_hash = configure(monkeypatch, tmp_path, mode)
    monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES", 64000)
    with pytest.raises(ExtractorExecutionError):
        await PdfTextItemExtractor().extract(path, file_hash, "test")
    assert not list((settings.DATA_DIR / "anchor_extractor").glob("*.json"))


async def test_valid_page_larger_than_default_asyncio_line_limit(monkeypatch, tmp_path):
    path, file_hash = configure(monkeypatch, tmp_path, "large_valid")
    stream = await PdfTextItemExtractor().extract(path, file_hash, "test")
    try:
        assert len(stream.pages[0].items) == 5
        assert len(stream.pages[0].items[0].text) == 20000
    finally:
        stream.close()


@pytest.mark.parametrize("termination", ["cancel", "idle", "total"])
async def test_cancel_and_timeout_reap_owned_child_tree(
    monkeypatch, tmp_path, termination
):
    path, file_hash = configure(monkeypatch, tmp_path, "hang")
    monkeypatch.setattr(
        settings,
        "PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS",
        5 if termination == "total" else 15,
    )
    monkeypatch.setattr(
        settings,
        "PDF_TEXTITEM_EXTRACTOR_IDLE_TIMEOUT_SECONDS",
        5 if termination == "idle" else 15,
    )
    work = asyncio.create_task(PdfTextItemExtractor().extract(path, file_hash, "test"))
    marker = settings.DATA_DIR / "anchor_extractor" / "owned-child.pid"
    for _ in range(80):
        if marker.exists():
            break
        await asyncio.sleep(0.05)
    assert marker.exists()
    child = int(marker.read_text())
    assert psutil.pid_exists(child)
    if termination == "cancel":
        work.cancel()
    with pytest.raises(
        asyncio.CancelledError if termination == "cancel" else ExtractorExecutionError
    ):
        await work
    assert not psutil.pid_exists(child)
    assert not list(marker.parent.glob("*.json"))


async def test_start_failure_cleans_options(monkeypatch, tmp_path):
    path, file_hash = configure(monkeypatch, tmp_path, "normal")
    monkeypatch.setattr(
        settings, "PDF_TEXTITEM_EXTRACTOR_COMMAND", '["a0-nonexistent-executable"]'
    )
    with pytest.raises(ExtractorUnavailableError):
        await PdfTextItemExtractor().extract(path, file_hash, "test")
    assert not list((settings.DATA_DIR / "anchor_extractor").glob("*.json"))


async def test_orphan_child_is_reaped_when_parent_exits_early(monkeypatch, tmp_path):
    path, file_hash = configure(monkeypatch, tmp_path, "orphan")
    with pytest.raises(ExtractorExecutionError):
        await PdfTextItemExtractor().extract(path, file_hash, "orphan")
    child = int(
        (settings.DATA_DIR / "anchor_extractor" / "owned-child.pid").read_text()
    )
    try:
        assert not psutil.pid_exists(child)
    finally:
        if psutil.pid_exists(child):
            psutil.Process(child).terminate()
