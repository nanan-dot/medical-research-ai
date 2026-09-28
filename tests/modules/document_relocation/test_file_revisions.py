"""A3 file change propagation acceptance."""

import pytest
from sqlalchemy import select

from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_relocation.file_versions import FileVersionService
from app.modules.document_relocation.model import AssetAnchorLink, DocumentFileRevision
from tests.modules.document_anchor.support import create_document


@pytest.mark.asyncio
async def test_file_change_stales_old_revision_without_rewriting_original_anchor(
    session, tmp_path
) -> None:
    document, _ = await create_document(session, tmp_path / "versioned")
    first_file = await FileVersionService(session).observe(document)
    anchor_revision = DocumentAnchorRevision(
        document_id=document.id,
        document_file_revision_id=first_file.id,
        file_hash=document.file_hash,
        request_fingerprint="f" * 64,
        extraction_fingerprint="e" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="o" * 64,
        state="ready",
    )
    session.add(anchor_revision)
    await session.flush()
    anchor = DocumentSourceAnchor(
        anchor_revision_id=anchor_revision.id,
        anchor_type="text_range",
        quote="Dose 5 mg",
        normalized_quote="Dose 5 mg",
        quote_hash="q" * 64,
        content_fingerprint="c" * 64,
        prefix="",
        suffix="",
        quality_status="eligible",
        resolution_status="exact",
    )
    session.add(anchor)
    await session.flush()
    link = AssetAnchorLink(
        asset_type="document_annotation",
        asset_id=99,
        original_anchor_id=anchor.id,
        resolved_anchor_id=anchor.id,
        resolution_status="anchored_exact",
        resolution_version=1,
    )
    session.add(link)
    await session.flush()

    old_hash = document.file_hash
    document.file_hash = "b" * 64
    document.file_size += 1
    second_file = await FileVersionService(session).observe(document)
    await session.flush()

    assert second_file.id != first_file.id
    assert first_file.file_hash == old_hash and not first_file.is_current
    assert (
        await session.get(DocumentAnchorRevision, anchor_revision.id)
    ).state == "stale"
    refreshed = await session.get(AssetAnchorLink, link.id)
    assert refreshed.original_anchor_id == anchor.id
    assert refreshed.resolved_anchor_id is None
    assert refreshed.resolution_status == "relocation_required"
    assert len(list((await session.scalars(select(DocumentFileRevision))).all())) == 2
