from pathlib import Path

from reportlab.pdfgen import canvas

from app.modules.document.parsers.pdf_parser import PDFParser


def make_pdf(path: Path, pages: list[list[tuple[float, float, str]]]) -> None:
    writer = canvas.Canvas(str(path))
    for page in pages:
        for x, y, text in page:
            writer.drawString(x, y, text)
        writer.showPage()
    writer.save()


def test_single_column_pdf_preserves_one_based_pages_and_removes_margins(tmp_path: Path):
    path = tmp_path / "single.pdf"
    make_pdf(
        path,
        [
            [
                (72, 800, "Repeated Header"),
                (72, 760, "Study Title"),
                (72, 720, "Page one body"),
                (72, 40, "Footer"),
            ],
            [(72, 800, "Repeated Header"), (72, 760, "Page two body"), (72, 40, "Footer")],
        ],
    )
    parsed = PDFParser().parse(path)
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert "Page one body" in parsed.pages[0].text
    assert "Page two body" in parsed.pages[1].text
    assert "Repeated Header" not in parsed.text
    assert "Footer" not in parsed.text
    assert parsed.is_scanned is False


def test_basic_two_column_pdf_extracts_both_columns(tmp_path: Path):
    path = tmp_path / "columns.pdf"
    make_pdf(path, [[(72, 760, "Left column"), (320, 760, "Right column")]])
    parsed = PDFParser().parse(path)
    assert "Left column" in parsed.text
    assert "Right column" in parsed.text


def test_empty_and_text_pages_keep_page_numbers(tmp_path: Path):
    path = tmp_path / "empty-page.pdf"
    make_pdf(path, [[], [(72, 760, "Second page text")]])
    parsed = PDFParser().parse(path)
    assert len(parsed.pages) == 2
    assert parsed.pages[0].page_number == 1
    assert parsed.pages[0].text == ""
    assert parsed.pages[1].page_number == 2


def test_blank_pdf_is_reported_as_scanned_without_ocr(tmp_path: Path):
    path = tmp_path / "scan.pdf"
    make_pdf(path, [[]])
    parsed = PDFParser().parse(path)
    assert parsed.is_scanned is True
    assert parsed.text == ""
