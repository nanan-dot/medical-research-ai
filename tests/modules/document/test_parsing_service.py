from pathlib import Path

import pytest

from app.common.exceptions import ConflictError
from app.modules.document.service import DocumentService
from app.modules.knowledge_source.sync_service import KnowledgeSourceSyncService
from tests.modules.document.conftest import create_document


@pytest.mark.asyncio
async def test_markdown_parse_persists_summary_and_status(session, tmp_path: Path):
    document, path = await create_document(session, tmp_path / "source", name="paper.md")
    path.write_text("---\ntitle: Notes\n---\n# Intro\nBody", encoding="utf-8")
    summary = await DocumentService(session).parse(document.id)
    assert summary.title == "Notes"
    assert summary.section_headings == ["Intro"]
    assert summary.character_count > 0
    assert document.parse_status == "succeeded"
    assert document.index_status == "outdated"
    stored = await DocumentService(session).content_summary(document.id)
    assert stored == summary


@pytest.mark.asyncio
async def test_invalid_yaml_sets_failed_and_never_succeeded(session, tmp_path: Path):
    document, path = await create_document(session, tmp_path / "source", name="broken.md")
    path.write_text("---\ntitle: [broken\n---\ntext", encoding="utf-8")
    with pytest.raises(ConflictError, match="invalid"):
        await DocumentService(session).parse(document.id)
    assert document.parse_status == "failed"
    assert document.error_code == "invalid_document_metadata"
    assert document.parsed_content is None


@pytest.mark.asyncio
async def test_unsupported_scanned_document_type_records_failure(session, tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "paper.docx").write_bytes(b"not parsed in WP04")
    source, _ = await create_document(session, root, name="placeholder.txt")
    source_record = await DocumentService(session).source_repo.get(source.knowledge_source_id)
    assert source_record is not None
    (root / "placeholder.txt").unlink()
    summary = await KnowledgeSourceSyncService(session).sync(source_record.id)
    assert summary.added == 1
    documents = await DocumentService(session).repo.list_by_source(source_record.id)
    docx = next(document for document in documents if document.file_path == "paper.docx")
    with pytest.raises(ConflictError, match=".docx"):
        await DocumentService(session).parse(docx.id)
    assert docx.parse_status == "failed"
    assert docx.error_code == "unsupported_document_type"
