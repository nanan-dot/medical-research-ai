"""A1 behavior tests derived from PDF_LAYOUT_SEGMENTATION_A1_DESIGN.md."""

from app.modules.document_layout.algorithm import (
    MAX_SEGMENT_CHARACTERS,
    MAX_SEGMENT_SOURCE_ITEMS,
    LayoutItem,
    segment_pages,
)


def _item(page: int, index: int, text: str, x: float, y: float) -> LayoutItem:
    return LayoutItem(page, index, text, x, y, 0.12, 0.02, "Arial", False)


def test_double_column_order_is_column_major_and_deterministic() -> None:
    pages = [
        [
            _item(1, 0, "Left first.", 0.08, 0.20),
            _item(1, 1, "Right first.", 0.56, 0.20),
            _item(1, 2, "Left second.", 0.08, 0.30),
            _item(1, 3, "Right second.", 0.56, 0.30),
        ]
    ]
    first = segment_pages(pages)
    second = segment_pages(pages)
    assert [segment.text for segment in first.segments] == [
        "Left first. Left second.",
        "Right first. Right second.",
    ]
    assert [(segment.key, segment.reading_order) for segment in first.segments] == [
        (segment.key, segment.reading_order) for segment in second.segments
    ]


def test_cross_page_paragraph_keeps_ordered_item_ranges() -> None:
    result = segment_pages(
        [
            [_item(1, 0, "Treatment continued", 0.08, 0.90)],
            [_item(2, 0, "without interruption.", 0.08, 0.12)],
        ]
    )
    assert len(result.segments) == 1
    assert result.segments[0].text == "Treatment continued without interruption."
    assert [
        (f.page_number, f.start_item_index, f.end_item_index)
        for f in result.segments[0].fragments
    ] == [(1, 0, 0), (2, 0, 0)]


def test_header_footer_are_auditable_but_not_normal_body_segments() -> None:
    result = segment_pages(
        [
            [
                _item(1, 0, "Journal of Tests", 0.2, 0.02),
                _item(1, 1, "Body one.", 0.1, 0.3),
                _item(1, 2, "1", 0.5, 0.97),
            ],
            [
                _item(2, 0, "Journal of Tests", 0.2, 0.02),
                _item(2, 1, "Body two.", 0.1, 0.3),
                _item(2, 2, "2", 0.5, 0.97),
            ],
        ]
    )
    assert [segment.text for segment in result.segments] == ["Body one.", "Body two."]
    assert any(block.block_type == "header" for block in result.blocks)
    assert any(block.block_type == "footer" for block in result.blocks)


def test_heading_sections_and_conservative_special_classification() -> None:
    result = segment_pages(
        [
            [
                _item(1, 0, "Results", 0.40, 0.10),
                _item(1, 1, "The dose was 5 mg.", 0.08, 0.20),
                _item(1, 2, "Table 1. Outcomes", 0.08, 0.50),
                _item(1, 3, "1. Smith A. Study.", 0.08, 0.80),
            ]
        ]
    )
    assert result.sections[0].literal_title == "Results"
    assert result.sections[0].canonical_role == "results"
    assert [segment.segment_type for segment in result.segments] == [
        "heading",
        "paragraph",
        "caption",
        "reference",
    ]
    assert result.segments[-1].translation_eligibility == "review_required"


def test_long_paragraph_is_split_before_it_reaches_anchor_protocol_limits() -> None:
    pages = []
    source_parts: list[str] = []
    for page_number in range(1, 9):
        page = []
        for item_index in range(40):
            text = f"clinical evidence item {page_number}-{item_index} continued"
            source_parts.append(text)
            page.append(_item(page_number, item_index, text, 0.08, 0.10 + item_index * 0.02))
        pages.append(page)

    result = segment_pages(pages)

    assert len(result.segments) > 1
    assert all(len(segment.text) <= MAX_SEGMENT_CHARACTERS for segment in result.segments)
    assert all(
        sum(fragment.end_item_index - fragment.start_item_index + 1 for fragment in segment.fragments)
        <= MAX_SEGMENT_SOURCE_ITEMS
        for segment in result.segments
    )
    assert " ".join(segment.text for segment in result.segments) == " ".join(source_parts)
