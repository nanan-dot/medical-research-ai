"""A0 设计 6/7/9 的反例，避免仅凭顺利提取就宣称完成。"""

import copy

import pytest

from app.modules.document_anchor.contract import (
    ContractValidationError,
    validate_records,
)
from app.modules.document_anchor.fingerprint import canonical_json
from app.modules.document_anchor.normalization import normalize_text_item
from app.modules.document_anchor.service import _page_entities
from tests.modules.document_anchor.support import seal
from tests.modules.document_anchor.test_acceptance import _header, _page, _trailer


def test_canonical_numbers_have_cross_runtime_identity() -> None:
    assert canonical_json({"n": 1}) == canonical_json({"n": 1.0})
    assert canonical_json({"n": -0.0}) == canonical_json({"n": 0})


def test_normalization_preserves_whitespace_and_soft_hyphen_with_utf16_map() -> None:
    raw = "e\u0301😀\u00ad 5−10 μg\x00"
    result = normalize_text_item(raw)
    assert result.normalized_text == "é😀\u00ad 5−10 μg"
    assert result.raw_utf16_length == len(raw.encode("utf-16-le")) // 2
    assert result.char_map[0] == (0, 2)
    assert result.char_map[1] == (2, 4)


@pytest.mark.parametrize("bad", [chr(0xD800), chr(0xDFFF)])
def test_illegal_unicode_is_rejected(bad: str) -> None:
    page = _page()
    page["items"][0]["text"] = bad
    with pytest.raises(ContractValidationError):
        validate_records([_header(), page, _trailer()])


def test_plain_blank_page_is_not_called_scanned() -> None:
    page, trailer = _page(), _trailer()
    page["items"] = []
    trailer["items_emitted"] = 0
    stream = validate_records(seal(_header(), [page], trailer))
    assert "NO_SELECTABLE_TEXT" in stream.quality_flags[0]
    assert "LIKELY_SCANNED_PAGE" not in stream.quality_flags[0]


def test_page_join_uses_previous_eol_and_records_synthetic_mapping() -> None:
    page, trailer = _page(), _trailer()
    second = copy.deepcopy(page["items"][0])
    second.update(item_index=1, source_array_index=2, text="next", has_eol=False)
    page["items"].append(second)
    trailer["items_emitted"] = 2
    stream = validate_records(seal(_header(), [page], trailer))
    entity, items = _page_entities(1, stream.pages[0], [], stream.page_hashes[0])
    assert entity.normalized_text == "Dose 5 mg\nnext"
    assert entity.raw_text == "Dose 5 mgnext"
    assert '"synthetic"' in entity.char_map_json
    assert items[1].normalized_char_start == 10
