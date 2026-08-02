"""Parser protocol and stable parser failures."""

from pathlib import Path
from typing import Protocol

from app.modules.document.parsers.schemas import ParsedDocument

MAX_DOCUMENT_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 10_000_000


class DocumentParserError(Exception):
    code = "document_parse_failed"


class UnsupportedDocumentTypeError(DocumentParserError):
    code = "unsupported_document_type"


class DocumentTooLargeError(DocumentParserError):
    code = "document_too_large"


class DocumentEncodingError(DocumentParserError):
    code = "document_encoding_error"


class InvalidDocumentMetadataError(DocumentParserError):
    code = "invalid_document_metadata"


class DocumentParser(Protocol):
    def parse(self, path: Path) -> ParsedDocument: ...


def validate_file_size(path: Path) -> None:
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise DocumentTooLargeError("Document exceeds the 100 MiB parsing limit")


def validate_extracted_size(text: str) -> None:
    if len(text) > MAX_EXTRACTED_CHARACTERS:
        raise DocumentTooLargeError("Extracted document text exceeds the safe limit")
