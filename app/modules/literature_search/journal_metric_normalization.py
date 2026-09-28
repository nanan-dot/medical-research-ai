"""期刊身份字段的确定性规范化。"""

from __future__ import annotations

import re
import unicodedata

_ISSN_BODY = re.compile(r"^[0-9]{7}[0-9X]$")
_TITLE_PUNCTUATION = re.compile(r"[^\w]+", re.UNICODE)


def is_valid_issn(value: str) -> bool:
    """按 ISO 3297 模 11 校验 ISSN。"""
    compact = re.sub(r"[\s-]", "", value).upper()
    if not _ISSN_BODY.fullmatch(compact):
        return False
    total = sum(
        int(character) * weight
        for character, weight in zip(compact[:7], range(8, 1, -1), strict=True)
    )
    expected = (11 - total % 11) % 11
    check = 10 if compact[-1] == "X" else int(compact[-1])
    return check == expected


def normalize_issn(value: str | None) -> str | None:
    """返回 NNNN-NNNN 形式的有效 ISSN，否则返回 None。"""
    if value is None:
        return None
    compact = re.sub(r"[\s-]", "", value).upper()
    if not is_valid_issn(compact):
        return None
    return f"{compact[:4]}-{compact[4:]}"


def normalize_journal_name(value: str | None) -> str | None:
    """仅用于完全匹配的期刊名规范化，不实施模糊推断。"""
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = " ".join(_TITLE_PUNCTUATION.sub(" ", normalized).split())
    return normalized or None
