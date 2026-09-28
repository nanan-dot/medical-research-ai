"""完整协议验证后的短事务发布，保留旧版本并批量写 TextItem。"""

import json
from datetime import UTC, datetime

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.modules.document_anchor.contract import ValidatedStream
from app.modules.document_anchor.fingerprint import extraction_fingerprint
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.page_builder import page_entities
from app.modules.document_anchor.quality import document_quality
from app.modules.document_anchor.repository import DocumentAnchorRepository
from app.modules.document_anchor.staging import StagedExtraction

Extraction = ValidatedStream | StagedExtraction


async def publish(
    session: AsyncSession, revision: DocumentAnchorRevision, stream: Extraction
) -> None:
    """Publish all rows or roll back all rows; caller owns the surrounding transaction."""
    fingerprint = extraction_fingerprint(
        revision.request_fingerprint, stream.document_hash
    )
    if revision.extraction_fingerprint is not None:
        if revision.extraction_fingerprint != fingerprint:
            raise ConflictError(
                "Diagnostic extraction differs from the immutable revision"
            )
        return
    page_ids = select(DocumentSourcePage.id).where(
        DocumentSourcePage.revision_id == revision.id
    )
    await session.execute(
        delete(DocumentSourceTextItem).where(
            DocumentSourceTextItem.page_id.in_(page_ids)
        )
    )
    await session.execute(
        delete(DocumentSourcePage).where(DocumentSourcePage.revision_id == revision.id)
    )
    counts: list[int] = []
    for record, page_flags, page_hash in zip(
        stream.pages, stream.quality_flags, stream.page_hashes, strict=True
    ):
        page, items = page_entities(revision.id, record, page_flags, page_hash)
        counts.append(len(items))
        session.add(page)
        await session.flush()
        for offset in range(0, len(items), 500):
            values = []
            for item in items[offset : offset + 500]:
                item.page_id = page.id
                values.append(
                    {
                        column.name: getattr(item, column.name)
                        for column in DocumentSourceTextItem.__table__.columns
                        if column.name != "id"
                    }
                )
            await session.execute(insert(DocumentSourceTextItem), values)
    await DocumentAnchorRepository(session).stale_other_visible(
        revision.document_id, revision.id
    )
    flags = stream.quality_flags
    revision.quality_summary_json = json.dumps(
        document_quality(counts, flags, stream.document_hash)
    )
    revision.extraction_fingerprint = fingerprint
    revision.state = "review_required" if any(flags) else "ready"
    revision.finished_at = datetime.now(UTC)
    revision.error_code = revision.error_message = None
    await session.flush()
