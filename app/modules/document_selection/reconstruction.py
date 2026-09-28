"""Pure reconstruction in A1 reading order with strict UTF-16 boundaries."""

from dataclasses import dataclass
from itertools import pairwise

from app.modules.document_anchor.normalization import normalize_text_item
from app.modules.document_anchor.selection_ranges import (
    SelectionRangeError,
    slice_utf16,
    utf16_length,
)
from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.schema import (
    MAX_CHARACTERS,
    MAX_PAGE_SPAN,
    SelectionFragment,
)


@dataclass(frozen=True)
class FlowItem:
    page_number: int
    item_index: int
    text: str
    segment_id: int
    rank: int
    eligibility: str


@dataclass(frozen=True)
class Reconstructed:
    quote: str
    fragments: tuple[SelectionFragment, ...]
    selected: tuple[tuple[FlowItem, int, int], ...]
    quality_status: str


def equivalent_text(text: str) -> str:
    """Only versioned NFC/control normalization and whitespace equivalence."""
    return " ".join(normalize_text_item(text).normalized_text.split())


def _expand(
    items: list[FlowItem], fragment: SelectionFragment
) -> list[tuple[FlowItem, int, int]]:
    candidates = sorted(
        (
            item
            for item in items
            if item.page_number == fragment.page_number
            and fragment.start_item_index <= item.item_index <= fragment.end_item_index
        ),
        key=lambda item: item.item_index,
    )
    if (
        not candidates
        or candidates[0].item_index != fragment.start_item_index
        or candidates[-1].item_index != fragment.end_item_index
    ):
        raise SelectionError("TEXT_ITEM_NOT_FOUND")
    selected = []
    for index, item in enumerate(candidates):
        start = fragment.start_offset_utf16 if index == 0 else 0
        end = (
            fragment.end_offset_utf16
            if index == len(candidates) - 1
            else utf16_length(item.text)
        )
        try:
            if start >= end:
                raise SelectionRangeError("empty UTF-16 range")
            slice_utf16(item.text, start, end)
        except (SelectionRangeError, UnicodeError) as error:
            raise SelectionError("UTF16_OFFSET_INVALID") from error
        selected.append((item, start, end))
    # 多 item 的数值区间不能跨栏折返；调用方可用逐 item fragments 表达正常选区。
    if any(right[0].rank != left[0].rank + 1 for left, right in pairwise(selected)):
        raise SelectionError("SELECTION_READING_ORDER_AMBIGUOUS")
    return selected


def reconstruct(
    items: list[FlowItem], fragments: list[SelectionFragment], browser_quote: str
) -> Reconstructed:
    """Rebuild a contiguous selection; reject skips, overlaps, symbols changed by client."""
    expanded = [(fragment, _expand(items, fragment)) for fragment in fragments]
    expanded.sort(key=lambda pair: (pair[1][0][0].rank, pair[1][0][1]))
    selected_with_fragments = [
        (entry, fragment) for fragment, entries in expanded for entry in entries
    ]
    selected = [entry for entry, _ in selected_with_fragments]
    if not selected:
        raise SelectionError("SELECTION_ENDPOINT_UNRESOLVED")
    if (
        max(item.page_number for item, _, _ in selected)
        - min(item.page_number for item, _, _ in selected)
        >= MAX_PAGE_SPAN
    ):
        raise SelectionError("SELECTION_LIMIT_EXCEEDED")
    if any(item.eligibility == "blocked" for item, _, _ in selected):
        raise SelectionError("SELECTION_CROSSES_BLOCKED_REGION")
    used_visual_gap = False
    for ((left, _, end), left_fragment), (
        (right, start, _),
        right_fragment,
    ) in pairwise(selected_with_fragments):
        if right.rank == left.rank and end == start:
            continue
        is_contiguous = (
            right.rank == left.rank + 1
            and end == utf16_length(left.text)
            and start == 0
        )
        # PDF text layers may store adjacent visual lines around another column's
        # item.  Per-item browser rectangles prove which visible glyph runs were
        # selected; accept only a small same-page gap and downgrade its quality.
        is_bounded_visual_gap = (
            1 < right.rank - left.rank <= 16
            and left.page_number == right.page_number
            and left_fragment.start_item_index == left_fragment.end_item_index
            and right_fragment.start_item_index == right_fragment.end_item_index
            and bool(left_fragment.rectangles)
            and bool(right_fragment.rectangles)
            and end == utf16_length(left.text)
            and start == 0
        )
        if not is_contiguous and not is_bounded_visual_gap:
            raise SelectionError("SELECTION_READING_ORDER_AMBIGUOUS")
        used_visual_gap = used_visual_gap or is_bounded_visual_gap
    parts: list[str] = []
    for index, (item, start, end) in enumerate(selected):
        if index and selected[index - 1][0].rank != item.rank:
            parts.append(" ")
        parts.append(slice_utf16(item.text, start, end))
    quote = "".join(parts)
    if not quote.strip() or len(quote) > MAX_CHARACTERS:
        raise SelectionError("SELECTION_LIMIT_EXCEEDED")
    if equivalent_text(quote) != equivalent_text(browser_quote):
        raise SelectionError(
            "QUOTE_MISMATCH", "浏览器选中文字与固定原文范围不一致，请刷新后重选"
        )
    quality = (
        "eligible"
        if not used_visual_gap
        and all(item.eligibility == "eligible" for item, _, _ in selected)
        else "review_required"
    )
    return Reconstructed(
        quote, tuple(fragment for fragment, _ in expanded), tuple(selected), quality
    )
