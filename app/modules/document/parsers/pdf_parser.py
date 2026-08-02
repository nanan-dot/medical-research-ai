"""Text-layer PDF parsing with one-based page tracking."""

from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from app.modules.document.parsers.base import (
    DocumentEncodingError,
    DocumentParserError,
    validate_extracted_size,
    validate_file_size,
)
from app.modules.document.parsers.schemas import ParsedDocument, ParsedPage


def _clean_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _remove_repeated_margins(page_texts: list[str]) -> list[str]:
    if len(page_texts) < 2:
        return page_texts
    first_lines: Counter[str] = Counter()
    last_lines: Counter[str] = Counter()
    split_pages: list[list[str]] = []
    for text in page_texts:
        lines = text.splitlines()
        split_pages.append(lines)
        if lines:
            first_lines[lines[0]] += 1
            last_lines[lines[-1]] += 1
    threshold = max(2, (len(page_texts) + 1) // 2)
    headers = {line for line, count in first_lines.items() if line and count >= threshold}
    footers = {line for line, count in last_lines.items() if line and count >= threshold}
    cleaned: list[str] = []
    for lines in split_pages:
        if lines and lines[0] in headers:
            lines = lines[1:]
        if lines and lines[-1] in footers:
            lines = lines[:-1]
        cleaned.append("\n".join(lines).strip())
    return cleaned


class PDFParser:
    def parse(self, path: Path) -> ParsedDocument:
        validate_file_size(path)
        try:
            reader = PdfReader(path)
            raw_pages = [_clean_text(page.extract_text() or "") for page in reader.pages]
        except DocumentParserError:
            raise
        except Exception as exc:
            raise DocumentParserError("PDF text extraction failed") from exc
        page_texts = _remove_repeated_margins(raw_pages)
        full_text = "\n\n".join(text for text in page_texts if text)
        validate_extracted_size(full_text)
        if full_text.count("�") > max(5, len(full_text) // 100):
            raise DocumentEncodingError("PDF text layer contains invalid character encoding")
        metadata_title = getattr(reader.metadata, "title", None) if reader.metadata else None
        first_line = next((line for text in page_texts for line in text.splitlines() if line), None)
        title = str(metadata_title).strip() if metadata_title else first_line
        if title and len(title) > 500:
            title = title[:500]
        non_whitespace = sum(not char.isspace() for char in full_text)
        is_scanned = bool(reader.pages) and non_whitespace < max(20, len(reader.pages) * 10)
        return ParsedDocument(
            source_path=str(path),
            title=title,
            text=full_text,
            pages=[
                ParsedPage(page_number=number, text=text)
                for number, text in enumerate(page_texts, start=1)
            ],
            is_scanned=is_scanned,
        )
