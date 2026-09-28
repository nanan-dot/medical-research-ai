"""基于已发布 A1 资产的抽取式章节包。"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_layout.model import (
    DocumentLayoutSection,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.document_reader.errors import (
    ReaderResourceNotFoundError,
    ReaderRevisionConflictError,
)


class ChapterBundleProjector:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def project(self, document_id: int, section_id: int, expected_anchor_revision_id: int, expected_segmentation_revision_id: int) -> dict[str, object]:
        anchor = await self._session.get(DocumentAnchorRevision, expected_anchor_revision_id)
        segmentation = await self._session.get(DocumentSegmentationRevision, expected_segmentation_revision_id)
        section = await self._session.get(DocumentLayoutSection, section_id)
        if anchor is None or anchor.document_id != document_id or segmentation is None or segmentation.anchor_revision_id != anchor.id:
            raise ReaderRevisionConflictError("章节 revision fence 已变化")
        if section is None or section.segmentation_revision_id != segmentation.id:
            raise ReaderResourceNotFoundError("章节不存在")
        segments = list((await self._session.scalars(select(DocumentLayoutSegment).where(DocumentLayoutSegment.segmentation_revision_id == segmentation.id, DocumentLayoutSegment.first_page <= section.last_page, DocumentLayoutSegment.last_page >= section.first_page).order_by(DocumentLayoutSegment.reading_order))).all())
        return {"section": {"id": section.id, "title": section.literal_title, "level": section.level, "first_page": section.first_page, "last_page": section.last_page}, "segments": [{"id": item.id, "segment_key": item.segment_key, "segment_type": item.segment_type, "text": item.text, "section_path": json.loads(item.section_path_json), "first_page": item.first_page, "last_page": item.last_page, "quality_flags": json.loads(item.quality_flags_json)} for item in segments], "revision_fence": {"anchor_revision_id": anchor.id, "segmentation_revision_id": segmentation.id}}

