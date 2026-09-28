"""Acceptance coverage for list/detail/preview capability consistency."""

from __future__ import annotations

from docx import Document as WordDocument


def test_preview_capability_matches_preview_service(library_client) -> None:
    """AC-LIB-14: PDF/DOCX are honestly previewable; other formats are not overstated."""
    client, seed, source_root = library_client
    docx_id = seed(relative_path="preview.docx", file_bytes=b"placeholder")
    docx_path = next(source_root.rglob("preview.docx"))
    word_document = WordDocument()
    word_document.add_paragraph("preview text")
    word_document.save(docx_path)
    markdown_id = seed(relative_path="no-preview.md")

    docx = client.get(f"/api/v1/library/items/{docx_id}")
    assert docx.status_code == 200
    assert docx.json()["preview_capability"] is True
    assert client.get(f"/api/v1/documents/{docx_id}/preview").json()["kind"] == "docx"
    markdown = client.get(f"/api/v1/library/items/{markdown_id}")
    assert markdown.json()["preview_capability"] is False
    assert client.get(f"/api/v1/documents/{markdown_id}/preview").json()["kind"] == "unavailable"
