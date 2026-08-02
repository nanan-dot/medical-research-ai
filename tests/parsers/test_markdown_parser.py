from pathlib import Path

import pytest

from app.modules.document.parsers.base import (
    DocumentEncodingError,
    DocumentTooLargeError,
    InvalidDocumentMetadataError,
    UnsupportedDocumentTypeError,
)
from app.modules.document.parsers.factory import create_parser
from app.modules.document.parsers.markdown_parser import MarkdownParser


def test_markdown_yaml_title_hierarchy_and_body(tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_text(
        "---\ntitle: Research Notes\ntags:\n  - methods\n---\n# Overview\nIntro\n## Methods\nDetails",
        encoding="utf-8",
    )
    parsed = MarkdownParser().parse(path)
    assert parsed.title == "Research Notes"
    assert parsed.yaml_metadata == {"title": "Research Notes", "tags": ["methods"]}
    assert [(section.heading, section.level) for section in parsed.sections] == [
        ("Overview", 1),
        ("Methods", 2),
    ]
    assert parsed.sections[1].text == "Details"
    assert parsed.source_path == str(path)


def test_invalid_yaml_has_stable_failure(tmp_path: Path):
    path = tmp_path / "invalid.md"
    path.write_text("---\ntitle: [broken\n---\n# Heading", encoding="utf-8")
    with pytest.raises(InvalidDocumentMetadataError, match="invalid"):
        MarkdownParser().parse(path)


def test_markdown_encoding_error(tmp_path: Path):
    path = tmp_path / "latin.md"
    path.write_bytes("café".encode("cp1252"))
    with pytest.raises(DocumentEncodingError, match="UTF-8"):
        MarkdownParser().parse(path)


def test_document_size_limit_is_enforced(tmp_path: Path, monkeypatch):
    path = tmp_path / "large.md"
    path.write_text("too large", encoding="utf-8")
    monkeypatch.setattr("app.modules.document.parsers.base.MAX_DOCUMENT_BYTES", 1)
    with pytest.raises(DocumentTooLargeError, match="100 MiB"):
        MarkdownParser().parse(path)


def test_unsupported_type_is_explicit(tmp_path: Path):
    with pytest.raises(UnsupportedDocumentTypeError, match=".docx"):
        create_parser(tmp_path / "paper.docx")
