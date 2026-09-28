"""A2 acceptance tests for browser UTF-16 selection ranges."""

import pytest

from app.modules.document_anchor.selection_ranges import (
    SelectionRangeError,
    slice_utf16,
    utf16_length,
)


def test_utf16_range_reconstructs_emoji_and_greek_text_without_mutation() -> None:
    text = "Dose 😀 α ≤ 5 mg"

    assert utf16_length(text) == 16
    assert slice_utf16(text, 5, 13) == "😀 α ≤ 5"


def test_utf16_range_rejects_surrogate_pair_midpoint() -> None:
    with pytest.raises(SelectionRangeError, match="UTF-16"):
        slice_utf16("A😀B", 2, 3)


@pytest.mark.parametrize("start,end", [(2, 2), (-1, 1), (0, 99), (3, 1)])
def test_utf16_invalid_empty_or_out_of_bounds_ranges(start: int, end: int) -> None:
    with pytest.raises(SelectionRangeError):
        slice_utf16("A😀B", start, end)


def test_combining_character_boundary_preserves_original_code_units() -> None:
    assert slice_utf16("e\u0301 α²", 0, 1) == "e"
    assert slice_utf16("e\u0301 α²", 1, 2) == "\u0301"


@pytest.mark.parametrize(
    ("text", "expected_utf16_length"),
    [
        ("α ≤ 5", 5),
        ("A😀B", 4),
        ("👩\u200d⚕️", 5),
        ("e\u0301", 2),
        ("✌️", 2),
        ("A\u00a0B", 3),
        ("co\u00adoperate", 10),
    ],
)
def test_unicode_adversarial_matrix_roundtrips_exact_utf16_ranges(
    text: str, expected_utf16_length: int
) -> None:
    assert utf16_length(text) == expected_utf16_length
    assert slice_utf16(text, 0, expected_utf16_length) == text
