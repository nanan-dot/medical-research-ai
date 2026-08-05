"""文献去重的纯函数：只判断候选，不写入数据库。"""

from __future__ import annotations

import re
import string
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from app.modules.literature_search.schema import CitationItem

MatchMethod = Literal["pmid", "doi", "title_normalized", "author_year", "manual"]
Confidence = Literal["clear", "fuzzy"]

DOI_PREFIX_PATTERN = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCTUATION_TRANSLATION = str.maketrans({character: " " for character in string.punctuation})


@dataclass(frozen=True)
class DedupRecord:
    """供匹配使用的不可变记录；record_id 由调用层定义且必须唯一。"""

    record_id: str
    item: CitationItem
    source_search_ids: tuple[int, ...]


@dataclass(frozen=True)
class DuplicateCandidate:
    """一组候选重复记录及可验证的匹配依据。"""

    records: tuple[DedupRecord, ...]
    match_method: MatchMethod
    confidence: Confidence


def normalize_doi(value: str | None) -> str | None:
    """标准化 DOI，保证前缀和大小写差异不影响精确匹配。"""
    if value is None:
        return None
    normalized = DOI_PREFIX_PATTERN.sub("", value.strip()).strip().lower()
    return normalized or None


def normalize_title(value: str | None) -> str | None:
    """标准化标题，供保守候选匹配使用，不推断翻译标题等价性。"""
    if value is None:
        return None
    normalized = value.lower().replace("&", " and ").translate(PUNCTUATION_TRANSLATION)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip().rstrip(".")
    return normalized or None


def find_duplicate_candidates(records: list[DedupRecord]) -> list[DuplicateCandidate]:
    """按优先级产出不重叠候选；同一记录只进入其最高优先级匹配组。"""
    unmatched_ids = {record.record_id for record in records}
    candidates: list[DuplicateCandidate] = []
    matching_rules: tuple[tuple[MatchMethod, Confidence, object], ...] = (
        ("pmid", "clear", lambda record: record.item.pmid.strip() or None),
        ("doi", "clear", lambda record: normalize_doi(record.item.doi)),
        ("title_normalized", "fuzzy", lambda record: normalize_title(record.item.title)),
        ("author_year", "fuzzy", _author_year_key),
    )
    for method, confidence, key_function in matching_rules:
        grouped: dict[str, list[DedupRecord]] = defaultdict(list)
        for record in records:
            if record.record_id not in unmatched_ids:
                continue
            key = key_function(record)  # type: ignore[operator]
            if key is not None:
                grouped[key].append(record)
        for group_records in grouped.values():
            if len(group_records) < 2:
                continue
            candidates.append(
                DuplicateCandidate(tuple(group_records), method, confidence)
            )
            unmatched_ids.difference_update(record.record_id for record in group_records)
    return candidates


def _author_year_key(record: DedupRecord) -> str | None:
    """只用首位作者和年份产生模糊候选，避免把其余作者误当成等价证据。"""
    if not record.item.authors or record.item.year is None:
        return None
    first_author = normalize_title(record.item.authors[0])
    if first_author is None:
        return None
    return f"{first_author}:{record.item.year}"
