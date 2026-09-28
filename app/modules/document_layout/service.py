"""A1 orchestration: authorize A0 input, derive outside publication, publish atomically."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_layout.algorithm import LayoutItem, segment_pages
from app.modules.document_layout.coordinates import natural_bbox
from app.modules.document_layout.model import (
    DocumentLayoutBlock,
    DocumentLayoutFragment,
    DocumentLayoutSection,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.document_layout.schema import (
    FragmentRead,
    SectionRead,
    SegmentationManifestRead,
    SegmentationRead,
    SegmentationState,
    SegmentPageRead,
    SegmentRead,
)
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository

ALGORITHM_VERSION = "a1-layout-4"
LAYOUT_CONFIG = {
    "baseline_tolerance": 0.015,
    "column_start_tolerance": 0.08,
    "cross_page": "conservative-v1",
    "max_segment_characters": 1200,
    "max_segment_source_items": 96,
    "max_segment_pages": 5,
}
CONFIG_HASH = sha256(json.dumps(LAYOUT_CONFIG, sort_keys=True).encode()).hexdigest()
TASK_TYPE = "document_layout_segmentation"


class SegmentationConflictError(ConflictError):
    code = "segmentation_conflict"


class DocumentLayoutService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._anchors = AnchorQueries(session)
        self._tasks = TaskRepository(session)

    async def request(
        self, anchor_revision_id: int, idempotency_key: str | None = None
    ) -> SegmentationRead:
        revision = await self._authorized_anchor(anchor_revision_id)
        if revision.state not in {"ready", "review_required"}:
            raise SegmentationConflictError(
                "Anchor revision is not ready for segmentation"
            )
        fingerprint = sha256(
            f"{revision.extraction_fingerprint}:{ALGORITHM_VERSION}:{CONFIG_HASH}".encode()
        ).hexdigest()
        existing = await self._session.scalar(
            select(DocumentSegmentationRevision).where(
                DocumentSegmentationRevision.anchor_revision_id == revision.id,
                DocumentSegmentationRevision.request_fingerprint == fingerprint,
            )
        )
        if existing and existing.state in {"ready", "review_required"}:
            return self._read(existing)
        if existing is None:
            existing = DocumentSegmentationRevision(
                anchor_revision_id=revision.id,
                request_fingerprint=fingerprint,
                algorithm_version=ALGORITHM_VERSION,
                config_hash=CONFIG_HASH,
                state="pending",
            )
            self._session.add(existing)
            await self._session.flush()
        key = idempotency_key or f"segment:{revision.id}:{fingerprint}"
        task = await self._tasks.find_active_by_key(key)
        if task is None:
            task = await self._tasks.create(
                TaskRecord(
                    task_type=TASK_TYPE,
                    title="PDF 版面与阅读顺序重建",
                    status="queued",
                    source_type="document_anchor_revision",
                    source_id=revision.id,
                    idempotency_key=key,
                    active_idempotency_key=key,
                    detail_json=json.dumps(
                        {
                            "segmentation_revision_id": existing.id,
                            "anchor_revision_id": revision.id,
                        },
                        separators=(",", ":"),
                    ),
                )
            )
        return self._read(existing, task.id)

    async def execute(
        self,
        segmentation_revision_id: int,
        task_id: int | None = None,
        worker_id: str | None = None,
    ) -> None:
        revision = await self._session.get(
            DocumentSegmentationRevision, segmentation_revision_id
        )
        if revision is None:
            raise NotFoundError("Segmentation revision not found")
        anchor = await self._authorized_anchor(revision.anchor_revision_id)
        pages = list(
            (
                await self._session.scalars(
                    select(DocumentSourcePage)
                    .where(DocumentSourcePage.revision_id == anchor.id)
                    .order_by(DocumentSourcePage.page_number)
                )
            ).all()
        )
        if not pages:
            raise SegmentationConflictError("Anchor revision has no published pages")
        page_by_id = {page.id: page for page in pages}
        items = list(
            (
                await self._session.scalars(
                    select(DocumentSourceTextItem)
                    .where(DocumentSourceTextItem.page_id.in_(page_by_id))
                    .order_by(
                        DocumentSourceTextItem.page_id,
                        DocumentSourceTextItem.item_index,
                    )
                )
            ).all()
        )
        grouped: dict[int, list[LayoutItem]] = {page.id: [] for page in pages}
        for item in items:
            bbox = json.loads(item.bbox_json)
            page = page_by_id[item.page_id]
            x, y, w, h = natural_bbox(bbox, json.loads(page.view_box_json), page.width, page.height, page.rotation)
            grouped[item.page_id].append(
                LayoutItem(
                    page.page_number,
                    item.item_index,
                    item.normalized_text,
                    x,
                    y,
                    w,
                    h,
                    item.font_name,
                    item.has_eol,
                )
            )
        result = segment_pages([grouped[page.id] for page in pages])
        # A0 已报告扫描/OCR/文本层异常时，A1 不得把几何猜测升级为可翻译正文。
        pages_requiring_review = {
            page.page_number for page in pages if json.loads(page.quality_flags_json)
        }
        unreliable_pages = {
            page.page_number
            for page in pages
            if any(
                marker in flag.casefold()
                for flag in json.loads(page.quality_flags_json)
                for marker in ("scan", "ocr", "low_text", "text_layer")
            )
        }
        if pages_requiring_review:
            result = replace(
                result,
                segments=tuple(
                    replace(
                        segment,
                        translation_eligibility=(
                            "blocked"
                            if any(
                                fragment.page_number in unreliable_pages
                                for fragment in segment.fragments
                            )
                            else "review_required"
                        ),
                        quality_flags=tuple(
                            sorted(
                                set(
                                    segment.quality_flags
                                    + (
                                        ("OCR_TEXT_UNRELIABLE",)
                                        if any(
                                            fragment.page_number in unreliable_pages
                                            for fragment in segment.fragments
                                        )
                                        else ("A0_PAGE_QUALITY_REVIEW",)
                                    )
                                )
                            )
                        ),
                    )
                    if any(
                        fragment.page_number in pages_requiring_review
                        for fragment in segment.fragments
                    )
                    else segment
                    for segment in result.segments
                ),
                quality_flags=tuple(
                    sorted(
                        {"A0_PAGE_QUALITY_REVIEW"}
                        | ({"OCR_TEXT_UNRELIABLE"} if unreliable_pages else set())
                    )
                ),
            )
        if task_id is not None and worker_id is not None:
            # 发布前重新获得 lease；取消或回收后的旧 worker 不得写入结果。
            has_lease = await self._tasks.renew_lease(task_id, worker_id, 60)
            if not has_lease:
                raise SegmentationConflictError("Layout task lease was lost")
        # No A1 rows become visible until all deterministic derivation is complete.
        async with self._session.begin_nested():
            await self._session.execute(
                delete(DocumentLayoutBlock).where(
                    DocumentLayoutBlock.segmentation_revision_id == revision.id
                )
            )
            await self._session.execute(
                delete(DocumentLayoutSection).where(
                    DocumentLayoutSection.segmentation_revision_id == revision.id
                )
            )
            await self._session.execute(
                delete(DocumentLayoutSegment).where(
                    DocumentLayoutSegment.segmentation_revision_id == revision.id
                )
            )
            for block in result.blocks:
                page = next(
                    page for page in pages if page.page_number == block.page_number
                )
                self._session.add(
                    DocumentLayoutBlock(
                        segmentation_revision_id=revision.id,
                        page_id=page.id,
                        block_order=block.block_order,
                        block_type=block.block_type,
                        text=block.text,
                        item_indexes_json=json.dumps(block.item_indexes),
                        bbox_json=json.dumps(
                            [block.x, block.y, block.width, block.height]
                        ),
                        quality_flags_json=json.dumps(block.quality_flags),
                    )
                )
            for section in result.sections:
                self._session.add(
                    DocumentLayoutSection(
                        segmentation_revision_id=revision.id,
                        literal_title=section.literal_title,
                        canonical_role=section.canonical_role,
                        level=section.level,
                        first_page=section.first_page,
                        last_page=section.last_page,
                    )
                )
            await self._session.flush()
            for segment in result.segments:
                stored = DocumentLayoutSegment(
                    segmentation_revision_id=revision.id,
                    segment_key=segment.key,
                    reading_order=segment.reading_order,
                    segment_type=segment.segment_type,
                    text=segment.text,
                    section_path_json=json.dumps(
                        segment.section_path, ensure_ascii=False
                    ),
                    translation_eligibility=segment.translation_eligibility,
                    quality_flags_json=json.dumps(segment.quality_flags),
                    first_page=segment.fragments[0].page_number,
                    last_page=segment.fragments[-1].page_number,
                )
                self._session.add(stored)
                await self._session.flush()
                for order, fragment in enumerate(segment.fragments):
                    page = next(
                        page
                        for page in pages
                        if page.page_number == fragment.page_number
                    )
                    self._session.add(
                        DocumentLayoutFragment(
                            segment_id=stored.id,
                            fragment_order=order,
                            page_id=page.id,
                            start_item_index=fragment.start_item_index,
                            end_item_index=fragment.end_item_index,
                        )
                    )
            output_hash = sha256(
                "|".join(item.key for item in result.segments).encode()
            ).hexdigest()
            revision.segmentation_fingerprint = sha256(
                f"{anchor.extraction_fingerprint}:{ALGORITHM_VERSION}:{CONFIG_HASH}:{output_hash}".encode()
            ).hexdigest()
            revision.quality_summary_json = json.dumps(
                {
                    "segment_count": len(result.segments),
                    "block_count": len(result.blocks),
                    "quality_flags": list(result.quality_flags),
                }
            )
            # The partial unique index permits only one current revision per A0.
            # Demote the previous publication before promoting this revision: an
            # autoflush caused by UPDATE must never observe two current rows.
            stale_revision_ids = select(DocumentSegmentationRevision.id).where(
                DocumentSegmentationRevision.anchor_revision_id == anchor.id,
                DocumentSegmentationRevision.id != revision.id,
                DocumentSegmentationRevision.state.in_(("ready", "review_required")),
            )
            # Speculative translations belong to a specific A1 generation.  Do
            # not spend model time on work that becomes unreachable immediately
            # after this publication.
            from app.modules.medical_translation.model import MedicalTranslationJob

            stale_segment_ids = select(DocumentLayoutSegment.id).where(
                DocumentLayoutSegment.segmentation_revision_id.in_(stale_revision_ids)
            )
            stale_job_ids = select(MedicalTranslationJob.id).where(
                MedicalTranslationJob.layout_segment_id.in_(stale_segment_ids),
                MedicalTranslationJob.state.in_(("queued", "running", "quality_checking")),
            )
            await self._session.execute(
                update(TaskRecord)
                .where(TaskRecord.id.in_(
                    select(MedicalTranslationJob.task_id).where(
                        MedicalTranslationJob.id.in_(stale_job_ids)
                    )
                ))
                .values(
                    status="cancelled",
                    phase="superseded",
                    active_idempotency_key=None,
                    lease_owner=None,
                    lease_expires_at=None,
                    finished_at=datetime.now(UTC),
                )
            )
            await self._session.execute(
                update(MedicalTranslationJob)
                .where(MedicalTranslationJob.id.in_(stale_job_ids))
                .values(
                    state="cancelled",
                    error_code="segmentation_superseded",
                    error_message="Translation generation was superseded",
                    finished_at=datetime.now(UTC),
                )
            )
            await self._session.execute(
                update(DocumentSegmentationRevision)
                .where(
                    DocumentSegmentationRevision.anchor_revision_id == anchor.id,
                    DocumentSegmentationRevision.id != revision.id,
                    DocumentSegmentationRevision.state.in_(
                        ("ready", "review_required")
                    ),
                )
                .values(state="stale")
            )
            revision.state = "review_required" if result.quality_flags else "ready"
            revision.finished_at = datetime.now(UTC)

    async def manifest(self, document_id: int) -> SegmentationManifestRead:
        await self._anchors.authorized_document(document_id)
        revision = await self._session.scalar(
            select(DocumentSegmentationRevision)
            .join(DocumentAnchorRevision)
            .where(
                DocumentAnchorRevision.document_id == document_id,
                DocumentSegmentationRevision.state.in_(("ready", "review_required")),
            )
            .order_by(DocumentSegmentationRevision.id.desc())
        )
        return SegmentationManifestRead(
            document_id=document_id,
            segmentation=self._read(revision) if revision else None,
        )

    async def segments(
        self, document_id: int, page: int | None, offset: int, limit: int,
        *, expected_anchor_revision_id: int | None = None,
        expected_segmentation_revision_id: int | None = None,
    ) -> SegmentPageRead:
        manifest = await self.manifest(document_id)
        if manifest.segmentation is None:
            raise NotFoundError("No published segmentation for document")
        # 可视段落必须与浏览器固定的 A0/A1 同代；换版后禁止把新段落挂到旧文本层。
        if (
            expected_anchor_revision_id is not None
            and expected_anchor_revision_id != manifest.segmentation.anchor_revision_id
        ) or (
            expected_segmentation_revision_id is not None
            and expected_segmentation_revision_id != manifest.segmentation.id
        ):
            raise SegmentationConflictError("Reader revision is no longer current")
        statement = select(DocumentLayoutSegment).where(
            DocumentLayoutSegment.segmentation_revision_id == manifest.segmentation.id
        )
        if page:
            statement = statement.where(
                DocumentLayoutSegment.first_page <= page,
                DocumentLayoutSegment.last_page >= page,
            )
        all_rows = list(
            (
                await self._session.scalars(
                    statement.order_by(DocumentLayoutSegment.reading_order)
                )
            ).all()
        )
        return SegmentPageRead(
            anchor_revision_id=manifest.segmentation.anchor_revision_id,
            segmentation_revision_id=manifest.segmentation.id,
            items=[
                await self._segment_read(row)
                for row in all_rows[offset : offset + limit]
            ],
            offset=offset,
            limit=limit,
            total=len(all_rows),
        )

    async def get_segment(self, segment_id: int) -> SegmentRead:
        row = await self._session.get(DocumentLayoutSegment, segment_id)
        if row is None:
            raise NotFoundError("Source segment not found")
        revision = await self._session.get(
            DocumentSegmentationRevision, row.segmentation_revision_id
        )
        assert revision is not None
        await self._authorized_anchor(revision.anchor_revision_id)
        return await self._segment_read(row)

    async def sections(self, document_id: int) -> list[SectionRead]:
        manifest = await self.manifest(document_id)
        if manifest.segmentation is None:
            raise NotFoundError("No published segmentation for document")
        rows = list(
            (
                await self._session.scalars(
                    select(DocumentLayoutSection)
                    .where(
                        DocumentLayoutSection.segmentation_revision_id
                        == manifest.segmentation.id
                    )
                    .order_by(
                        DocumentLayoutSection.first_page, DocumentLayoutSection.id
                    )
                )
            ).all()
        )
        return [
            SectionRead(
                id=x.id,
                literal_title=x.literal_title,
                canonical_role=x.canonical_role,
                level=x.level,
                first_page=x.first_page,
                last_page=x.last_page,
            )
            for x in rows
        ]

    async def section_segments(
        self, document_id: int, section_id: int, offset: int, limit: int
    ) -> SegmentPageRead:
        manifest = await self.manifest(document_id)
        if manifest.segmentation is None:
            raise NotFoundError("No published segmentation for document")
        section = await self._session.get(DocumentLayoutSection, section_id)
        if (
            section is None
            or section.segmentation_revision_id != manifest.segmentation.id
        ):
            raise NotFoundError("Section not found for document")
        rows = list(
            (
                await self._session.scalars(
                    select(DocumentLayoutSegment)
                    .where(
                        DocumentLayoutSegment.segmentation_revision_id
                        == manifest.segmentation.id
                    )
                    .order_by(DocumentLayoutSegment.reading_order)
                )
            ).all()
        )
        # 页码范围只是导航摘要：一页可以顺序包含多个章节。章节内容必须
        # 以已发布的 heading 阅读顺序为边界，不能把同页的下一章节混入。
        heading_index = next(
            (
                index
                for index, row in enumerate(rows)
                if row.segment_type == "heading"
                and json.loads(row.section_path_json) == [section.literal_title]
            ),
            None,
        )
        if heading_index is None:
            raise SegmentationConflictError("Section has no published heading segment")
        next_heading_index = next(
            (
                index
                for index in range(heading_index + 1, len(rows))
                if rows[index].segment_type == "heading"
            ),
            len(rows),
        )
        rows = rows[heading_index:next_heading_index]
        return SegmentPageRead(
            items=[
                await self._segment_read(row) for row in rows[offset : offset + limit]
            ],
            offset=offset,
            limit=limit,
            total=len(rows),
        )

    async def _authorized_anchor(
        self, anchor_revision_id: int
    ) -> DocumentAnchorRevision:
        revision = await self._session.get(DocumentAnchorRevision, anchor_revision_id)
        if revision is None:
            raise NotFoundError("Anchor revision not found")
        await self._anchors.authorized_document(revision.document_id)
        return revision

    def _read(
        self, row: DocumentSegmentationRevision, task_id: int | None = None
    ) -> SegmentationRead:
        return SegmentationRead(
            id=row.id,
            anchor_revision_id=row.anchor_revision_id,
            state=SegmentationState(row.state),
            task_id=task_id,
            algorithm_version=row.algorithm_version,
            config_hash=row.config_hash,
            segmentation_fingerprint=row.segmentation_fingerprint,
            quality_summary=json.loads(row.quality_summary_json),
            created_at=row.created_at,
            finished_at=row.finished_at,
        )

    async def _segment_read(self, row: DocumentLayoutSegment) -> SegmentRead:
        fragments = list(
            (
                await self._session.execute(
                    select(DocumentLayoutFragment, DocumentSourcePage.page_number)
                    .join(
                        DocumentSourcePage,
                        DocumentLayoutFragment.page_id == DocumentSourcePage.id,
                    )
                    .where(DocumentLayoutFragment.segment_id == row.id)
                    .order_by(DocumentLayoutFragment.fragment_order)
                )
            ).all()
        )
        return SegmentRead(
            id=row.id,
            segment_key=row.segment_key,
            reading_order=row.reading_order,
            segment_type=row.segment_type,
            text=row.text,
            section_path=json.loads(row.section_path_json),
            translation_eligibility=row.translation_eligibility,
            quality_flags=json.loads(row.quality_flags_json),
            first_page=row.first_page,
            last_page=row.last_page,
            fragments=[
                FragmentRead(
                    page_number=p,
                    start_item_index=f.start_item_index,
                    end_item_index=f.end_item_index,
                )
                for f, p in fragments
            ],
        )
