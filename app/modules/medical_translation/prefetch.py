"""Bounded background preparation of translations for ready PDF segments."""

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_layout.model import (
    DocumentLayoutFragment,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.medical_translation.constants import (
    PHASE2_MAX_SEGMENTS_PER_INTENT,
    PHASE2_PREFETCH_QUEUE_LIMIT,
)
from app.modules.medical_translation.model import MedicalTranslationJob
from app.modules.medical_translation.schema import TranslationSegmentIntentCreate
from app.modules.medical_translation.service import MedicalTranslationService


class DocumentTranslationPrefetchScheduler:
    """Keep a small low-priority queue filled without delaying live selections."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def run_once(self) -> bool:
        async with self._factory() as session:
            active_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(MedicalTranslationJob)
                    .where(
                        MedicalTranslationJob.request_trigger == "prefetch",
                        MedicalTranslationJob.state.in_(
                            ("queued", "running", "quality_checking")
                        ),
                    )
                )
                or 0
            )
            capacity = PHASE2_PREFETCH_QUEUE_LIMIT - active_count
            if capacity <= 0:
                return False
            revisions = list((await session.scalars(
                select(DocumentSegmentationRevision)
                .join(
                    DocumentAnchorRevision,
                    DocumentAnchorRevision.id
                    == DocumentSegmentationRevision.anchor_revision_id,
                )
                .join(Document, Document.id == DocumentAnchorRevision.document_id)
                .where(
                    DocumentSegmentationRevision.state.in_(("ready", "review_required")),
                    DocumentAnchorRevision.state.in_(("ready", "review_required")),
                    Document.file_hash == DocumentAnchorRevision.file_hash,
                )
                .order_by(DocumentSegmentationRevision.finished_at.desc())
            )).all())
            existing_segment_ids = select(
                MedicalTranslationJob.layout_segment_id
            ).where(MedicalTranslationJob.layout_segment_id.is_not(None))
            limit = min(PHASE2_MAX_SEGMENTS_PER_INTENT, capacity)
            for revision in revisions:
                anchor = await session.get(
                    DocumentAnchorRevision, revision.anchor_revision_id
                )
                if anchor is None:
                    continue
                document = await session.get(Document, anchor.document_id)
                if document is None:
                    continue
                candidates = list((await session.scalars(
                        select(DocumentLayoutSegment)
                        .where(
                            DocumentLayoutSegment.segmentation_revision_id
                            == revision.id,
                            DocumentLayoutSegment.translation_eligibility
                            == "eligible",
                            DocumentLayoutSegment.id.not_in(existing_segment_ids),
                        )
                        .order_by(DocumentLayoutSegment.reading_order)
                    )).all())
                if not candidates:
                    continue
                count_rows = (await session.execute(
                    select(
                        DocumentLayoutFragment.segment_id,
                        func.sum(
                            DocumentLayoutFragment.end_item_index
                            - DocumentLayoutFragment.start_item_index
                            + 1
                        ),
                    )
                    .where(DocumentLayoutFragment.segment_id.in_([item.id for item in candidates]))
                    .group_by(DocumentLayoutFragment.segment_id)
                )).all()
                counts: dict[int, int] = {
                    int(segment_id): int(count or 0)
                    for segment_id, count in count_rows
                }
                segments = [
                    segment for segment in candidates
                    if len(segment.text) <= 8_000
                    and int(counts.get(segment.id, 0)) <= 256
                    and segment.last_page - segment.first_page < 5
                ][:limit]
                if not segments:
                    continue
                result = await MedicalTranslationService(session).request_segments(
                    document.id,
                    TranslationSegmentIntentCreate(
                        expected_file_hash=document.file_hash,
                        expected_anchor_revision_id=anchor.id,
                        expected_segmentation_revision_id=revision.id,
                        segment_ids=[segment.id for segment in segments],
                        active_segment_id=None,
                        trigger="prefetch",
                    ),
                )
                await session.commit()
                if result.queued_count > 0:
                    return True
            return False
