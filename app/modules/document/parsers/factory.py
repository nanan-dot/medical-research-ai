"""Select parsers without leaking third-party types to services."""

from pathlib import Path

from app.modules.document.parsers.base import DocumentParser, UnsupportedDocumentTypeError
from app.modules.document.parsers.markdown_parser import MarkdownParser
from app.modules.document.parsers.pdf_parser import PDFParser


def create_parser(path: Path) -> DocumentParser:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        return PDFParser()
    if suffix == ".md":
        return MarkdownParser()
    raise UnsupportedDocumentTypeError(f"No parser is available for {suffix or 'this file type'}")
