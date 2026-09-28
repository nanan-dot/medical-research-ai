"""SW Copilot 阅读上下文 revision 与作用域校验。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.schema import MessageCreate
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_layout.model import (
    DocumentLayoutSection,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.document_reader.errors import (
    ReaderResourceNotFoundError,
    ReaderRevisionConflictError,
)


async def validate_copilot_context(
    session: AsyncSession,
    payload: MessageCreate,
    allowed_document_ids: set[int] | None = None,
) -> None:
    context_fields = (
        payload.document_id,
        payload.source_anchor_id,
        payload.active_segment_id,
        payload.section_id,
        payload.expected_anchor_revision_id,
        payload.expected_segmentation_revision_id,
    )
    if not any(value is not None for value in context_fields):
        return
    if payload.document_id is None or payload.expected_anchor_revision_id is None:
        raise ValueError("document_id and expected_anchor_revision_id are required for reader context")
    if allowed_document_ids is not None and payload.document_id not in allowed_document_ids:
        raise ReaderResourceNotFoundError("阅读上下文不属于该会话")
    anchor_revision = await session.get(DocumentAnchorRevision, payload.expected_anchor_revision_id)
    if anchor_revision is None or anchor_revision.document_id != payload.document_id:
        raise ReaderRevisionConflictError("Copilot anchor revision 已变化")
    if payload.expected_segmentation_revision_id is not None:
        segmentation = await session.get(DocumentSegmentationRevision, payload.expected_segmentation_revision_id)
        if segmentation is None or segmentation.anchor_revision_id != anchor_revision.id:
            raise ReaderRevisionConflictError("Copilot segmentation revision 已变化")
    if payload.source_anchor_id is not None:
        source_anchor = await session.get(DocumentSourceAnchor, payload.source_anchor_id)
        if source_anchor is None or source_anchor.anchor_revision_id != anchor_revision.id:
            raise ReaderResourceNotFoundError("SourceAnchor 不属于当前 revision")
    if payload.active_segment_id is not None:
        segment = await session.get(DocumentLayoutSegment, payload.active_segment_id)
        if segment is None or segment.segmentation_revision_id != payload.expected_segmentation_revision_id:
            raise ReaderResourceNotFoundError("active segment 不属于当前 revision")
    if payload.section_id is not None:
        section = await session.get(DocumentLayoutSection, payload.section_id)
        if section is None or section.segmentation_revision_id != payload.expected_segmentation_revision_id:
            raise ReaderResourceNotFoundError("section 不属于当前 revision")
