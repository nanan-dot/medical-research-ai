"""Create immutable source anchors from authorized, pinned A0/A1 inputs."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.document_anchor.model import (
    DocumentAnchorFragment,
    DocumentAnchorRevision,
    DocumentSourceAnchor,
    DocumentSourcePage,
)
from app.modules.document_anchor.normalization import normalize_text_item
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_anchor.selection_ranges import slice_utf16, utf16_length
from app.modules.document_selection.context import SelectionContext, load_context
from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.model import DocumentAnchorSegment
from app.modules.document_selection.reconstruction import Reconstructed, reconstruct
from app.modules.document_selection.schema import (
    AnchorRead,
    SelectionFragment,
    SourceAnchorDescriptor,
)

CONTEXT_CHARACTERS = 128


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SourceAnchorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, document_id: int, descriptor: SourceAnchorDescriptor
    ) -> AnchorRead:
        context = await load_context(self._session, document_id, descriptor)
        result = reconstruct(
            context.flow, descriptor.fragments, descriptor.browser_quote
        )
        ranges = [
            (item.page_number, item.item_index, start, end)
            for item, start, end in result.selected
        ]
        fingerprint = digest(
            json.dumps(
                [context.anchor.id, ranges, digest(result.quote)], separators=(",", ":")
            )
        )
        existing = await self._session.scalar(
            select(DocumentSourceAnchor).where(
                DocumentSourceAnchor.content_fingerprint == fingerprint
            )
        )
        async with self._session.begin_nested():
            if existing is None:
                first, start, _ = result.selected[0]
                last, _, end = result.selected[-1]
                existing = DocumentSourceAnchor(
                    anchor_revision_id=context.anchor.id,
                    anchor_type="multi_segment"
                    if len({item.segment_id for item, _, _ in result.selected}) > 1
                    else "text_range",
                    quote=result.quote,
                    normalized_quote=normalize_text_item(result.quote).normalized_text,
                    quote_hash=digest(result.quote),
                    content_fingerprint=fingerprint,
                    prefix=(
                        " ".join(
                            item.text for item in context.flow if item.rank < first.rank
                        )
                        + " "
                        + slice_utf16(first.text, 0, start)
                    )[-CONTEXT_CHARACTERS:],
                    suffix=(
                        slice_utf16(last.text, end, utf16_length(last.text))
                        + " "
                        + " ".join(
                            item.text for item in context.flow if item.rank > last.rank
                        )
                    )[:CONTEXT_CHARACTERS],
                    quality_status=result.quality_status,
                    resolution_status="exact",
                )
                self._session.add(existing)
                await self._session.flush()
                for order, fragment in enumerate(result.fragments):
                    # The full descriptor has already been reconstructed and quote-
                    # checked. A PDF.js flow can legitimately contain a position-only
                    # whitespace item between visible glyph runs; hashing that stored
                    # fragment directly preserves the exact A0 mapping without trying
                    # to treat whitespace alone as a user-visible selection.
                    fragment_quote = _fragment_quote(context, fragment)
                    self._session.add(
                        DocumentAnchorFragment(
                            anchor_id=existing.id,
                            fragment_order=order,
                            page_id=context.pages[fragment.page_number].id,
                            start_item_index=fragment.start_item_index,
                            end_item_index=fragment.end_item_index,
                            start_offset_utf16=fragment.start_offset_utf16,
                            end_offset_utf16=fragment.end_offset_utf16,
                            rectangles_json=json.dumps(
                                [rect.model_dump() for rect in fragment.rectangles]
                            ),
                            reconstructed_text_hash=digest(fragment_quote),
                        )
                    )
            await self._coverage(existing.id, context, result)
            await self._session.flush()
        return await self.get(existing.id, document_id)

    async def _coverage(
        self, anchor_id: int, context: SelectionContext, result: Reconstructed
    ) -> None:
        exists = await self._session.scalar(
            select(DocumentAnchorSegment.id).where(
                DocumentAnchorSegment.anchor_id == anchor_id,
                DocumentAnchorSegment.segmentation_revision_id == context.layout.id,
            )
        )
        if exists is not None:
            return
        segment_ids = list(
            dict.fromkeys(item.segment_id for item, _, _ in result.selected)
        )
        for order, segment_id in enumerate(segment_ids):
            # A0 may contain position-only whitespace TextItems.  A1's segment
            # text intentionally omits them, so they must not manufacture extra
            # separators during the exact coverage comparison below.
            segment_items = [
                (
                    item,
                    normalize_text_item(item.text).normalized_text.strip(),
                )
                for item in context.flow
                if item.segment_id == segment_id
            ]
            segment_items = [item for item in segment_items if item[1]]
            texts = [text for _, text in segment_items]
            if " ".join(texts) != context.segments[segment_id].text:
                raise SelectionError("TEXT_MAPPING_INCOMPLETE")
            cursor = 0
            covered: list[int] = []
            for item_position, (item, text) in enumerate(segment_items):
                normalized = normalize_text_item(item.text)
                trim = len(normalized.normalized_text) - len(
                    normalized.normalized_text.lstrip()
                )
                for selected, start, end in result.selected:
                    if selected.rank == item.rank:
                        for normalized_index, (raw_start, raw_end) in enumerate(
                            normalized.char_map
                        ):
                            if (
                                raw_start < end
                                and raw_end > start
                                and trim <= normalized_index < trim + len(text)
                            ):
                                covered.append(cursor + normalized_index - trim)
                cursor += len(text)
                if item_position < len(segment_items) - 1:
                    cursor += 1
            if not covered:
                raise SelectionError("TEXT_MAPPING_INCOMPLETE")
            first, last = min(covered), max(covered) + 1
            self._session.add(
                DocumentAnchorSegment(
                    anchor_id=anchor_id,
                    segmentation_revision_id=context.layout.id,
                    segment_id=segment_id,
                    coverage_order=order,
                    segment_char_start=first,
                    segment_char_end=last,
                    coverage_type="full"
                    if first == 0 and last == len(context.segments[segment_id].text)
                    else "partial",
                )
            )

    async def get(
        self,
        anchor_id: int,
        document_id: int | None = None,
        *,
        require_current: bool = False,
    ) -> AnchorRead:
        anchor = await self._session.get(DocumentSourceAnchor, anchor_id)
        if anchor is None:
            raise NotFoundError("Source anchor not found")
        revision = await self._session.get(
            DocumentAnchorRevision, anchor.anchor_revision_id
        )
        if revision is None:
            raise NotFoundError("Source revision not found")
        document = await AnchorQueries(self._session).authorized_document(
            revision.document_id, fresh=True
        )
        if document_id is not None and document_id != revision.document_id:
            raise SelectionError("ANCHOR_DOCUMENT_MISMATCH")
        current = document.file_hash == revision.file_hash and revision.state in {
            "ready",
            "review_required",
        }
        if require_current and not current:
            raise SelectionError("ANCHOR_REVISION_CONFLICT")
        rows = (
            await self._session.execute(
                select(DocumentAnchorFragment, DocumentSourcePage.page_number)
                .join(
                    DocumentSourcePage,
                    DocumentSourcePage.id == DocumentAnchorFragment.page_id,
                )
                .where(DocumentAnchorFragment.anchor_id == anchor.id)
                .order_by(DocumentAnchorFragment.fragment_order)
            )
        ).all()
        memberships = list(
            (
                await self._session.scalars(
                    select(DocumentAnchorSegment)
                    .where(DocumentAnchorSegment.anchor_id == anchor.id)
                    .order_by(
                        DocumentAnchorSegment.segmentation_revision_id.desc(),
                        DocumentAnchorSegment.coverage_order,
                    )
                )
            ).all()
        )
        latest = memberships[0].segmentation_revision_id if memberships else None
        return AnchorRead(
            id=anchor.id,
            document_id=revision.document_id,
            anchor_revision_id=revision.id,
            file_hash=revision.file_hash,
            extraction_fingerprint=revision.extraction_fingerprint,
            quote=anchor.quote,
            quote_hash=anchor.quote_hash,
            resolution_status="exact" if current else "unresolved",
            quality_status="eligible"
            if anchor.quality_status == "eligible"
            else "review_required",
            fragments=[
                SelectionFragment(
                    page_number=page_number,
                    start_item_index=row.start_item_index,
                    end_item_index=row.end_item_index,
                    start_offset_utf16=row.start_offset_utf16,
                    end_offset_utf16=row.end_offset_utf16,
                    rectangles=json.loads(row.rectangles_json),
                )
                for row, page_number in rows
            ],
            segment_ids=[
                row.segment_id
                for row in memberships
                if row.segmentation_revision_id == latest
            ],
            created_at=anchor.created_at,
        )


def _fragment_quote(context: SelectionContext, fragment: SelectionFragment) -> str:
    items = sorted(
        (
            item
            for item in context.flow
            if item.page_number == fragment.page_number
            and fragment.start_item_index <= item.item_index <= fragment.end_item_index
        ),
        key=lambda item: item.rank,
    )
    return " ".join(
        slice_utf16(
            item.text,
            fragment.start_offset_utf16
            if item.item_index == fragment.start_item_index
            else 0,
            fragment.end_offset_utf16
            if item.item_index == fragment.end_item_index
            else utf16_length(item.text),
        )
        for item in items
    )
