"""Pure, deterministic geometry-to-segment reconstruction for A1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from json import dumps

# Keep A1 output comfortably inside the A2 selection protocol (8,000 characters,
# 256 source fragments and five pages).  Headroom accounts for normalization
# differences between reconstructed block text and raw PDF.js items.
MAX_SEGMENT_CHARACTERS = 1_200
MAX_SEGMENT_SOURCE_ITEMS = 96
MAX_SEGMENT_PAGES = 5


@dataclass(frozen=True)
class LayoutItem:
    page_number: int
    item_index: int
    text: str
    x: float
    y: float
    width: float
    height: float
    font_name: str | None
    has_eol: bool


@dataclass(frozen=True)
class Fragment:
    page_number: int
    start_item_index: int
    end_item_index: int


@dataclass(frozen=True)
class LayoutBlock:
    page_number: int
    block_order: int
    block_type: str
    text: str
    item_indexes: tuple[int, ...]
    x: float
    y: float
    width: float
    height: float
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Segment:
    key: str
    reading_order: int
    segment_type: str
    text: str
    fragments: tuple[Fragment, ...]
    section_path: tuple[str, ...]
    translation_eligibility: str
    quality_flags: tuple[str, ...]


@dataclass(frozen=True)
class Section:
    literal_title: str
    canonical_role: str | None
    level: int
    first_page: int
    last_page: int


@dataclass(frozen=True)
class SegmentationResult:
    blocks: tuple[LayoutBlock, ...]
    segments: tuple[Segment, ...]
    sections: tuple[Section, ...]
    quality_flags: tuple[str, ...]


_HEADING_ROLES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "methods": "methods",
    "materials and methods": "methods",
    "patients and methods": "methods",
    "results": "results",
    "findings": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
    "supplement": "supplement",
    "supplementary material": "supplement",
}
_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*\s+\S")
_REFERENCE = re.compile(r"^\d+[.)]\s+\S")
_CAPTION = re.compile(r"^(?:figure|fig\.?|table)\s*\d+", re.IGNORECASE)
_LIST = re.compile(r"^(?:[-•▪]|\d+[.)])\s+")


def _clean_join(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip())


def _kind(text: str, y: float) -> str:
    lowered = text.strip().casefold()
    if y < 0.06:
        return "header"
    if y > 0.94:
        return "footer"
    if lowered in _HEADING_ROLES or _NUMBERED_HEADING.match(text):
        return "heading"
    if _CAPTION.match(text):
        return "caption"
    if _REFERENCE.match(text):
        return "reference"
    if _LIST.match(text):
        return "list_item"
    return "paragraph"


def _blocks_for_page(items: list[LayoutItem]) -> list[LayoutBlock]:
    # 同一基线的 PDF.js item 合并为行；容忍导出器的微小浮点误差。
    ordered = sorted(
        items, key=lambda value: (round(value.y, 3), value.x, value.item_index)
    )
    lines: list[list[LayoutItem]] = []
    for item in ordered:
        # 同一基线但明显横跨栏间空白时必须拆行，否则会把双栏拼成一行。
        has_column_gap = bool(
            lines and item.x - max(value.x + value.width for value in lines[-1]) > 0.20
        )
        if not lines or abs(lines[-1][0].y - item.y) > 0.015 or has_column_gap:
            lines.append([item])
        else:
            lines[-1].append(item)
    raw: list[LayoutBlock] = []
    for index, line in enumerate(lines):
        line.sort(key=lambda value: (value.x, value.item_index))
        text = _clean_join([value.text for value in line])
        if not text:
            continue
        x = min(value.x for value in line)
        right = max(value.x + value.width for value in line)
        raw.append(
            LayoutBlock(
                line[0].page_number,
                index,
                _kind(text, line[0].y),
                text,
                tuple(value.item_index for value in line),
                x,
                line[0].y,
                right - x,
                max(value.height for value in line),
            )
        )
    # 宽行是跨栏标题；正文按 X 带排序后，各栏内上到下，这是双栏不串列的关键。
    main = [block for block in raw if block.block_type not in {"header", "footer"}]
    starts = sorted(
        {
            round(block.x, 2)
            for block in main
            if block.block_type != "heading" and block.width < 0.45
        }
    )
    columns = starts if len(starts) <= 3 else starts[:3]

    def reading_key(block: LayoutBlock) -> tuple[int, float, float]:
        column = (
            min(range(len(columns)), key=lambda i: abs(columns[i] - round(block.x, 2)))
            if columns
            else 0
        )
        return (column, block.y, block.x)

    body = sorted(main, key=reading_key)
    special = [block for block in raw if block.block_type in {"header", "footer"}]
    return [*body, *special]


def _merge_paragraphs(blocks: list[LayoutBlock]) -> list[LayoutBlock]:
    merged: list[LayoutBlock] = []
    for block in blocks:
        if block.block_type != "paragraph" or not merged:
            merged.append(block)
            continue
        previous = merged[-1]
        same_column = abs(previous.x - block.x) < 0.08
        close = block.y - previous.y < 0.16
        if previous.block_type == "paragraph" and same_column and close:
            merged[-1] = LayoutBlock(
                previous.page_number,
                previous.block_order,
                "paragraph",
                _clean_join([previous.text, block.text]),
                previous.item_indexes + block.item_indexes,
                previous.x,
                previous.y,
                max(previous.width, block.width),
                previous.height + block.height,
            )
        else:
            merged.append(block)
    return merged


def _split_oversized_blocks(
    blocks: list[LayoutBlock], items: list[LayoutItem]
) -> list[LayoutBlock]:
    """Split merged paragraphs at stable PDF item boundaries before publication."""
    text_by_index = {item.item_index: item.text for item in items}
    bounded: list[LayoutBlock] = []
    for block in blocks:
        groups: list[list[int]] = [[]]
        for item_index in block.item_indexes:
            candidate = [*groups[-1], item_index]
            candidate_text = _clean_join([text_by_index.get(index, "") for index in candidate])
            if groups[-1] and (
                len(candidate) > MAX_SEGMENT_SOURCE_ITEMS
                or len(candidate_text) > MAX_SEGMENT_CHARACTERS
            ):
                groups.append([item_index])
            else:
                groups[-1] = candidate
        for group in groups:
            text = _clean_join([text_by_index.get(index, "") for index in group])
            if not text:
                continue
            flags = block.quality_flags
            if len(text) > MAX_SEGMENT_CHARACTERS:
                flags = (*flags, "source_item_exceeds_translation_limit")
            bounded.append(
                LayoutBlock(
                    block.page_number,
                    block.block_order,
                    block.block_type,
                    text,
                    tuple(group),
                    block.x,
                    block.y,
                    block.width,
                    block.height,
                    flags,
                )
            )
    return bounded


def _can_cross_page(previous: LayoutBlock, current: LayoutBlock) -> bool:
    return (
        previous.block_type == current.block_type == "paragraph"
        and previous.text.rstrip()[-1:] not in ".?!:;"
        and abs(previous.x - current.x) < 0.08
    )


def _can_extend_segment(prior: Segment, current: LayoutBlock) -> bool:
    combined_pages = {fragment.page_number for fragment in prior.fragments}
    combined_pages.add(current.page_number)
    return (
        len(_clean_join([prior.text, current.text])) <= MAX_SEGMENT_CHARACTERS
        and sum(
            fragment.end_item_index - fragment.start_item_index + 1
            for fragment in prior.fragments
        )
        + len(current.item_indexes)
        <= MAX_SEGMENT_SOURCE_ITEMS
        and len(combined_pages) <= MAX_SEGMENT_PAGES
    )


def segment_pages(pages: list[list[LayoutItem]]) -> SegmentationResult:
    all_blocks: list[LayoutBlock] = []
    body: list[LayoutBlock] = []
    for page in pages:
        page_blocks = _split_oversized_blocks(
            _merge_paragraphs(_blocks_for_page(page)), page
        )
        all_blocks.extend(page_blocks)
        body.extend(
            block
            for block in page_blocks
            if block.block_type not in {"header", "footer"}
        )
    segments: list[Segment] = []
    sections: list[Section] = []
    path: list[str] = []
    for block_index, block in enumerate(body):
        if block.block_type == "heading":
            role = _HEADING_ROLES.get(block.text.strip().casefold())
            path = [block.text]
            sections.append(
                Section(block.text, role, 1, block.page_number, block.page_number)
            )
        fragment = Fragment(
            block.page_number, min(block.item_indexes), max(block.item_indexes)
        )
        if (
            segments
            and block_index > 0
            and _can_cross_page(body[block_index - 1], block)
            and _can_extend_segment(segments[-1], block)
        ):
            prior = segments[-1]
            segments[-1] = Segment(
                prior.key,
                prior.reading_order,
                prior.segment_type,
                _clean_join([prior.text, block.text]),
                prior.fragments + (fragment,),
                prior.section_path,
                prior.translation_eligibility,
                prior.quality_flags,
            )
            continue
        eligibility = (
            "review_required"
            if block.block_type in {"caption", "reference", "list_item"}
            or "source_item_exceeds_translation_limit" in block.quality_flags
            else "eligible"
        )
        payload = (
            block.block_type,
            block.text,
            [
                (
                    fragment.page_number,
                    fragment.start_item_index,
                    fragment.end_item_index,
                )
            ],
        )
        key = sha256(
            dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        segments.append(
            Segment(
                key,
                len(segments),
                block.block_type,
                block.text,
                (fragment,),
                tuple(path),
                eligibility,
                block.quality_flags,
            )
        )
    return SegmentationResult(tuple(all_blocks), tuple(segments), tuple(sections), ())
