"""NFC 与可追溯 UTF-16 源范围；不猜测词、栏或语义。"""

import unicodedata
from dataclasses import dataclass

NORMALIZATION_VERSION = "textitem-norm-2"


def utf16_length(text: str) -> int:
    """Return browser-compatible code-unit length; reject lone surrogates."""
    return len(text.encode("utf-16-le")) // 2


@dataclass(frozen=True)
class NormalizedText:
    raw_text: str
    normalized_text: str
    normalization_version: str
    removed_control_character_count: int
    raw_utf16_length: int
    char_map: tuple[tuple[int, int], ...]


def _canonical_order(tokens: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """Stable canonical ordering in O(n log n), including hostile combining runs."""
    ordered: list[tuple[str, int, int]] = []
    group: list[tuple[str, int, int]] = []
    for token in tokens:
        if unicodedata.combining(token[0]) == 0:
            ordered.extend(
                sorted(group, key=lambda item: unicodedata.combining(item[0]))
            )
            group = []
        group.append(token)
    ordered.extend(sorted(group, key=lambda item: unicodedata.combining(item[0])))
    return ordered


def normalize_text_item(raw_text: str) -> NormalizedText:
    """Normalize NFC, retaining conservative source UTF-16 ranges per output codepoint."""
    raw_length = utf16_length(raw_text)
    tokens: list[tuple[str, int, int]] = []
    cursor = 0
    removed = 0
    for char in raw_text:
        end = cursor + utf16_length(char)
        if unicodedata.category(char) == "Cc" and char not in "\t\n\r":
            removed += 1
        else:
            tokens.extend(
                (part, cursor, end) for part in unicodedata.normalize("NFD", char)
            )
        cursor = end
    tokens = _canonical_order(tokens)
    normalized = unicodedata.normalize("NFC", "".join(token[0] for token in tokens))
    # NFC 可跨过不可组合标记组成复合字符，不能按每个输出字符的 NFD 长度顺序切源。
    output_tokens = _canonical_order(
        [
            (part, index, index)
            for index, char in enumerate(normalized)
            for part in unicodedata.normalize("NFD", char)
        ]
    )
    ranges: list[list[tuple[int, int]]] = [[] for _ in normalized]
    for source, output in zip(tokens, output_tokens, strict=True):
        if source[0] != output[0]:
            raise ValueError("NFC provenance mismatch")
        ranges[output[1]].append((source[1], source[2]))
    mapping = tuple(
        (min(start for start, _ in values), max(end for _, end in values))
        for values in ranges
    )
    return NormalizedText(
        raw_text, normalized, NORMALIZATION_VERSION, removed, raw_length, mapping
    )
