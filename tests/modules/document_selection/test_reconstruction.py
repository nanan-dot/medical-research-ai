"""A2 synthetic fixtures: immutable text ranges, never medical gold labels."""

import pytest

from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.reconstruction import FlowItem, reconstruct
from app.modules.document_selection.schema import SelectionFragment


def fragment(page: int, index: int, start: int, end: int) -> SelectionFragment:
    return SelectionFragment(
        page_number=page,
        start_item_index=index,
        end_item_index=index,
        start_offset_utf16=start,
        end_offset_utf16=end,
    )


def test_reverse_cross_page_selection_preserves_symbols_and_ranges() -> None:
    items = [
        FlowItem(1, 2, "Dose 😀", 1, 0, "eligible"),
        FlowItem(2, 0, "α ≤ 5 mg", 1, 1, "eligible"),
    ]
    result = reconstruct(
        items, [fragment(2, 0, 0, 8), fragment(1, 2, 5, 7)], "😀 α ≤ 5 mg"
    )
    assert result.quote == "😀 α ≤ 5 mg"
    assert [part.page_number for part in result.fragments] == [1, 2]


@pytest.mark.parametrize("quote", ["Dose 50 mg", "Dose −5 mg", "Dose 5 mg <"])
def test_forged_quote_is_rejected(quote: str) -> None:
    with pytest.raises(SelectionError) as error:
        reconstruct(
            [FlowItem(1, 0, "Dose 5 mg", 1, 0, "eligible")],
            [fragment(1, 0, 0, 9)],
            quote,
        )
    assert error.value.code == "QUOTE_MISMATCH"


def test_interleaved_item_indexes_follow_layout_order_not_numeric_range() -> None:
    items = [
        FlowItem(1, 0, "Left", 1, 0, "eligible"),
        FlowItem(1, 2, "continued", 1, 1, "eligible"),
        FlowItem(1, 1, "Right", 2, 2, "eligible"),
    ]
    result = reconstruct(
        items, [fragment(1, 0, 0, 4), fragment(1, 2, 0, 9)], "Left continued"
    )
    assert result.quote == "Left continued"
    with pytest.raises(SelectionError):
        reconstruct(
            items,
            [
                SelectionFragment(
                    page_number=1,
                    start_item_index=0,
                    end_item_index=2,
                    start_offset_utf16=0,
                    end_offset_utf16=9,
                )
            ],
            "Left continued",
        )


def test_gap_and_blocked_selection_cannot_become_exact() -> None:
    items = [
        FlowItem(1, 0, "One", 1, 0, "eligible"),
        FlowItem(1, 1, "Table", 2, 1, "blocked"),
        FlowItem(1, 2, "Two", 3, 2, "eligible"),
    ]
    for fragments, quote in [
        ([fragment(1, 0, 0, 3), fragment(1, 2, 0, 3)], "One Two"),
        ([fragment(1, 1, 0, 5)], "Table"),
    ]:
        with pytest.raises(SelectionError):
            reconstruct(items, fragments, quote)


def test_visual_text_layer_fragments_may_cross_a_small_layout_rank_gap() -> None:
    items = [
        FlowItem(1, 91, "Laboratory of Molecular Medicine,", 1, 0, "eligible"),
        FlowItem(1, 94, "2", 2, 1, "eligible"),
        FlowItem(1, 92, "Heraklion, Greece.", 1, 2, "eligible"),
    ]
    rectangles = [{"left": 0.1, "top": 0.2, "width": 0.4, "height": 0.02}]
    selected = [
        fragment(1, 91, 0, len(items[0].text)).model_copy(
            update={"rectangles": rectangles}
        ),
        fragment(1, 92, 0, len(items[2].text)).model_copy(
            update={"rectangles": rectangles}
        ),
    ]

    result = reconstruct(
        items, selected, "Laboratory of Molecular Medicine, Heraklion, Greece."
    )

    assert result.quality_status == "review_required"
    assert [part.start_item_index for part in result.fragments] == [91, 92]


def test_same_quote_at_different_positions_keeps_distinct_ranges() -> None:
    items = [
        FlowItem(1, 0, "Repeat", 1, 0, "eligible"),
        FlowItem(1, 1, "Repeat", 2, 1, "eligible"),
    ]
    first = reconstruct(items, [fragment(1, 0, 0, 6)], "Repeat")
    second = reconstruct(items, [fragment(1, 1, 0, 6)], "Repeat")
    assert first.quote == second.quote
    assert first.fragments != second.fragments
