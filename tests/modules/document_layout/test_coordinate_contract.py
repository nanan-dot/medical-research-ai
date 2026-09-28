"""A0 corner-coordinate contract, including real PDF.js extraction."""

from datetime import UTC, datetime

import pytest

from app.modules.document_anchor.extractor_runner import PdfTextItemExtractor
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_anchor.publisher import publish
from app.modules.document_layout.service import DocumentLayoutService
from tests.modules.document_anchor.support import create_document


@pytest.mark.asyncio
async def test_real_pdfjs_body_is_not_misclassified_as_header(session, tmp_path):
    document, path = await create_document(session, tmp_path / "real-body")
    revision = DocumentAnchorRevision(document_id=document.id, file_hash=document.file_hash,
        request_fingerprint="d" * 64, extractor_version="x", pdfjs_version="6.2.108",
        normalization_version="textitem-norm-2", options_hash="x" * 64,
        state="pending", created_at=datetime.now(UTC))
    session.add(revision)
    await session.flush()
    stream = await PdfTextItemExtractor().extract(path, document.file_hash, "a2-coordinate-contract")
    try:
        await publish(session, revision, stream)
    finally:
        stream.close()
    layout = await DocumentLayoutService(session).request(revision.id)
    await DocumentLayoutService(session).execute(layout.id)
    await session.commit()
    result = await DocumentLayoutService(session).segments(document.id, 1, 0, 10)
    assert [segment.text for segment in result.items] == ["Dose 5 mg"]
