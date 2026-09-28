"""自制可再分发 PDF 的确定性、复杂版式与安全行为。"""

import asyncio
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pytest
import reportlab
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.common.exceptions import UnprocessableEntityError
from app.core.config import settings
from app.modules.document_anchor.extractor_runner import (
    ExtractorExecutionError,
    PdfTextItemExtractor,
)


def complex_pdf(path: Path) -> None:
    font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    pdfmetrics.registerFont(TTFont("A0Vera", str(font_path)))
    pdf = canvas.Canvas(str(path), invariant=1)
    pdf.setFont("Symbol", 12)
    pdf.drawString(40, 790, "α β μ")
    pdf.setFont("A0Vera", 12)
    for column in (40, 310):
        for row in range(20):
            pdf.drawString(column, 750 - row * 20, f"Row {row}: 5 mg p<0.05 5−10")
    pdf.showPage()
    pdf.showPage()
    bitmap = io.BytesIO()
    Image.new("RGB", (100, 100), "gray").save(bitmap, format="PNG")
    bitmap.seek(0)
    pdf.drawImage(ImageReader(bitmap), 0, 0, 500, 700)
    pdf.showPage()
    pdf.setPageRotation(90)
    pdf.drawString(40, 40, "Rotated text")
    pdf.save()


async def test_real_mixed_pdf_is_deterministic_and_matches_reader(tmp_path):
    path = tmp_path / "two columns and symbols.pdf"
    complex_pdf(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    progress = []

    async def observe(completed, total):
        progress.append((completed, total))

    extractor = PdfTextItemExtractor(observe)
    first = await extractor.extract(path, sha, "first")
    second = await extractor.extract(path, sha, "second")
    try:
        assert first.document_hash == second.document_hash
        assert first.page_hashes == second.page_hashes
        assert "α β μ" in "".join(item.text for item in first.pages[0].items)
        assert "NO_SELECTABLE_TEXT" in first.quality_flags[1]
        assert "LIKELY_SCANNED_PAGE" not in first.quality_flags[1]
        assert "LIKELY_SCANNED_PAGE" in first.quality_flags[2]
        assert first.pages[3].rotation == 90
        assert progress[0] == (0, 4) and progress[-1] == (4, 4)
        output = await asyncio.to_thread(
            subprocess.run,
            ["node", str(Path(__file__).with_name("reader_items.mjs")), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        reader = json.loads(output.stdout)
        for actual, expected in zip(first.pages, reader, strict=True):
            assert [
                {"text": item.text, "transform": list(item.transform)}
                for item in actual.items
            ] == expected
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize(
    "kind,code",
    [
        ("encrypted", "encrypted_pdf"),
        ("corrupt", "invalid_pdf"),
        ("pages", "resource_limit_exceeded"),
        ("items", "resource_limit_exceeded"),
        ("output", "resource_limit_exceeded"),
    ],
)
async def test_real_pdf_failures_have_safe_classified_errors(
    tmp_path, monkeypatch, kind, code
):
    path = tmp_path / "sensitive title.pdf"
    complex_pdf(path)
    if kind == "encrypted":
        writer = PdfWriter(clone_from=path)
        writer.encrypt("fixture-password")
        writer.write(path)
    elif kind == "corrupt":
        path.write_bytes(b"%PDF-1.7\nnot a valid object")
    elif kind == "pages":
        monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_MAX_PAGES", 1)
    elif kind == "items":
        monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE", 1)
    elif kind == "output":
        monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES", 200)
    with pytest.raises(ExtractorExecutionError) as failure:
        await PdfTextItemExtractor().extract(
            path, hashlib.sha256(path.read_bytes()).hexdigest(), "failure"
        )
    assert failure.value.code == code
    assert str(path) not in str(failure.value) and "sensitive" not in str(failure.value)


async def test_pdf_javascript_and_attachment_are_inert(tmp_path):
    path = tmp_path / "attachment.pdf"
    pdf = canvas.Canvas(str(path), invariant=1)
    pdf.drawString(10, 50, "visible text")
    pdf.save()
    writer = PdfWriter(clone_from=path)
    writer.add_js('throw new Error("A0_SCRIPT_MUST_NOT_EXECUTE");')
    writer.add_attachment("a0-attachment.txt", b"ATTACHMENT_MUST_NOT_ENTER_TEXT_LAYER")
    writer.write(path)
    assert "/Names" in PdfReader(path).trailer["/Root"]
    stream = await PdfTextItemExtractor().extract(
        path, hashlib.sha256(path.read_bytes()).hexdigest(), "inert"
    )
    try:
        assert "".join(item.text for item in stream.pages[0].items) == "visible text"
    finally:
        stream.close()


async def test_file_size_limit_is_enforced_before_process_start(tmp_path, monkeypatch):
    path = tmp_path / "large.pdf"
    complex_pdf(path)
    monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES", 100)
    with pytest.raises(UnprocessableEntityError):
        await PdfTextItemExtractor().extract(
            path, hashlib.sha256(path.read_bytes()).hexdigest(), "size"
        )
