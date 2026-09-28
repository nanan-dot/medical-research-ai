"""Load and fence the versioned A0/A1 read context before any source write."""

import json
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_layout.model import (
    DocumentLayoutBlock,
    DocumentLayoutFragment,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.reconstruction import FlowItem
from app.modules.document_selection.schema import SelectionVersion


@dataclass
class SelectionContext:
    anchor: DocumentAnchorRevision
    layout: DocumentSegmentationRevision
    pages: dict[int, DocumentSourcePage]
    items: dict[tuple[int, int], DocumentSourceTextItem]
    flow: list[FlowItem]
    segments: dict[int, DocumentLayoutSegment]


async def load_context(
    session: AsyncSession,
    document_id: int,
    descriptor: SelectionVersion,
    *,
    fence: bool = True,
) -> SelectionContext:
    document = await AnchorQueries(session).authorized_document(document_id, fresh=True)
    if document.file_hash != descriptor.expected_file_hash:
        raise SelectionError("DOCUMENT_REVISION_CONFLICT")
    anchor = await session.get(
        DocumentAnchorRevision,
        descriptor.expected_anchor_revision_id,
        populate_existing=True,
    )
    if (
        anchor is None
        or anchor.document_id != document_id
        or anchor.file_hash != document.file_hash
        or anchor.state not in {"ready", "review_required"}
    ):
        raise SelectionError("ANCHOR_REVISION_CONFLICT")
    layout = await session.get(
        DocumentSegmentationRevision,
        descriptor.expected_segmentation_revision_id,
        populate_existing=True,
    )
    if (
        layout is None
        or layout.anchor_revision_id != anchor.id
        or layout.state not in {"ready", "review_required"}
    ):
        raise SelectionError("SEGMENTATION_REVISION_CONFLICT")
    # SQLite 写锁在业务事务结束前保持，换版与并发 get-or-create 不可穿过此检查。
    if fence:
        locked_id = await session.scalar(
            update(Document)
            .where(
                Document.id == document_id,
                Document.file_hash == descriptor.expected_file_hash,
            )
            .values(file_hash=descriptor.expected_file_hash)
            .returning(Document.id)
        )
        if locked_id is None:
            raise SelectionError("DOCUMENT_REVISION_CONFLICT")
        # 同一写事务内再次刷新 A0/A1，挡住读取和获得写锁之间的版本变化。
        await session.refresh(anchor)
        await session.refresh(layout)
        if anchor.state not in {"ready", "review_required"}:
            raise SelectionError("ANCHOR_REVISION_CONFLICT")
        if layout.state not in {"ready", "review_required"}:
            raise SelectionError("SEGMENTATION_REVISION_CONFLICT")
    pages = list(
        (
            await session.scalars(
                select(DocumentSourcePage).where(
                    DocumentSourcePage.revision_id == anchor.id
                )
            )
        ).all()
    )
    page_by_id = {page.id: page for page in pages}
    stored = list(
        (
            await session.scalars(
                select(DocumentSourceTextItem).where(
                    DocumentSourceTextItem.page_id.in_(page_by_id)
                )
            )
        ).all()
    )
    items = {
        (page_by_id[item.page_id].page_number, item.item_index): item for item in stored
    }
    segments = list(
        (
            await session.scalars(
                select(DocumentLayoutSegment)
                .where(DocumentLayoutSegment.segmentation_revision_id == layout.id)
                .order_by(DocumentLayoutSegment.reading_order)
            )
        ).all()
    )
    blocks = list(
        (
            await session.scalars(
                select(DocumentLayoutBlock).where(
                    DocumentLayoutBlock.segmentation_revision_id == layout.id
                )
            )
        ).all()
    )
    fragments = list(
        (
            await session.scalars(
                select(DocumentLayoutFragment)
                .where(
                    DocumentLayoutFragment.segment_id.in_(
                        [segment.id for segment in segments]
                    )
                )
                .order_by(DocumentLayoutFragment.fragment_order)
            )
        ).all()
    )
    flow = _build_flow(segments, blocks, fragments, page_by_id, items)
    return SelectionContext(
        anchor,
        layout,
        {page.page_number: page for page in pages},
        items,
        flow,
        {segment.id: segment for segment in segments},
    )


def _build_flow(
    segments: list[DocumentLayoutSegment],
    blocks: list[DocumentLayoutBlock],
    fragments: list[DocumentLayoutFragment],
    pages: dict[int, DocumentSourcePage],
    items: dict[tuple[int, int], DocumentSourceTextItem],
) -> list[FlowItem]:
    flow: list[FlowItem] = []
    seen: set[tuple[int, int]] = set()
    for segment in segments:
        for fragment in (
            value for value in fragments if value.segment_id == segment.id
        ):
            candidates = [
                json.loads(block.item_indexes_json)
                for block in blocks
                if block.page_id == fragment.page_id
                and block.block_type not in {"header", "footer"}
                and json.loads(block.item_indexes_json)
                and min(json.loads(block.item_indexes_json))
                == fragment.start_item_index
                and max(json.loads(block.item_indexes_json)) == fragment.end_item_index
            ]
            if len(candidates) != 1:
                raise SelectionError("SELECTION_READING_ORDER_AMBIGUOUS")
            page = pages[fragment.page_id]
            for item_index in candidates[0]:
                key = (page.page_number, item_index)
                if key in seen or key not in items:
                    raise SelectionError("SELECTION_READING_ORDER_AMBIGUOUS")
                seen.add(key)
                item = items[key]
                if not item.raw_text:
                    continue
                eligibility = segment.translation_eligibility
                if item.direction not in {"ltr", ""} or json.loads(
                    page.quality_flags_json
                ):
                    eligibility = "blocked"
                flow.append(
                    FlowItem(*key, item.raw_text, segment.id, len(flow), eligibility)
                )
    return flow
