"""完整/篡改协议及跨运行时哈希验收。"""

import copy
import json
import subprocess

import pytest

from app.modules.document_anchor.contract import (
    ContractValidationError,
    validate_records,
)
from app.modules.document_anchor.fingerprint import canonical_json, request_fingerprint
from app.modules.document_anchor.normalization import normalize_text_item
from app.modules.document_anchor.page_builder import separator
from app.modules.document_anchor.toolchain import identity
from tests.modules.document_anchor.support import seal
from tests.modules.document_anchor.test_acceptance import _header, _page, _trailer


@pytest.mark.parametrize(
    "mutation",
    [
        "header",
        "trailer",
        "jump",
        "duplicate",
        "nan",
        "width",
        "source",
        "type",
        "hash",
        "document_hash",
        "schema",
        "pdfjs",
        "request",
        "style",
        "unicode",
    ],
)
def test_tampered_stream_never_validates(mutation):
    records = seal(_header(), [_page()], _trailer())
    if mutation == "header":
        records.insert(1, records[0])
    elif mutation == "trailer":
        records.pop()
    elif mutation == "jump":
        records[1]["page_number"] = 2
    elif mutation == "duplicate":
        records.insert(2, records[1])
    elif mutation == "nan":
        records[1]["width"] = float("nan")
    elif mutation == "width":
        records[1]["items"][0]["width"] = -1
    elif mutation == "source":
        records[1]["items"][0]["source_array_index"] = -1
    elif mutation == "type":
        records[1]["record_type"] = "anything"
    elif mutation == "hash":
        records[1]["items"][0]["text"] = "tampered"
    elif mutation == "document_hash":
        records[-1]["document_content_hash"] = "f" * 64
    elif mutation == "schema":
        records[0]["contract_schema_version"] = "99"
    elif mutation == "pdfjs":
        records[0]["pdfjs_version"] = "0.1"
    elif mutation == "request":
        records[-1]["request_id"] = "wrong"
    elif mutation == "style":
        records[1]["styles"]["f1"]["untrusted"] = "x"
    elif mutation == "unicode":
        records[1]["items"][0]["text"] = chr(0xD800)
    with pytest.raises(ContractValidationError):
        validate_records(records)


@pytest.mark.parametrize(
    "value",
    [
        1,
        -0.0,
        1e-7,
        1e20,
        5e-324,
        {"😀": ["é", True, None, 1.25], "a": 0},
        {"n": 9007199254740991, "z": "\u2028\u2029"},
    ],
)
def test_node_python_canonical_golden_vectors(value):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            'import {canonicalJson} from "./tools/pdf_textitem_extractor/dist/checksum.js"; process.stdout.write(canonicalJson(JSON.parse(process.argv[1])));',
            "--",
            json.dumps(value, ensure_ascii=True),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert result.stdout == canonical_json(value)


def test_every_toolchain_input_changes_request_identity():
    base = ["a" * 64, "1.1.0", "6.2.108", "textitem-norm-2", identity()["options_hash"]]
    first = request_fingerprint(*base)
    for index in range(len(base)):
        changed = base.copy()
        changed[index] += "x"
        assert request_fingerprint(*changed) != first


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("\u1100\u1161\u11a8", "각"),
        ("a\u0315\u0300", "à\u0315"),
        ("5  mg\t−10 μg", "5  mg\t−10 μg"),
        ("a\x00b", "ab"),
    ],
)
def test_nfc_mapping_keeps_source_ranges(raw, expected):
    result = normalize_text_item(raw)
    assert result.normalized_text == expected
    assert len(result.char_map) == len(expected)
    assert all(
        0 <= start < end <= result.raw_utf16_length for start, end in result.char_map
    )


def test_geometric_separator_does_not_split_adjacent_glyphs():
    page = _page()
    previous = page["items"][0]
    previous.update(text="dose-", has_eol=False, width=10)
    current = copy.deepcopy(previous)
    current.update(item_index=1, source_array_index=1, text="response")
    current["transform"][4] += 10
    page["items"].append(current)
    trailer = _trailer()
    trailer["items_emitted"] = 2
    stream = validate_records(seal(_header(), [page], trailer))
    first, second = stream.pages[0].items
    assert separator(first, second) == ""
    second.transform = (
        *second.transform[:4],
        second.transform[4] + 20,
        second.transform[5],
    )
    assert separator(first, second) == " "
    first.has_eol = True
    assert separator(first, second) == "\n"


def test_nfc_composition_across_reordered_mark_keeps_each_origin():
    result = normalize_text_item("a\u0327\u0301")
    assert result.normalized_text == "á\u0327"
    assert result.char_map == ((0, 3), (1, 2))
