"""润色事实保护：数字、年份、PMID/DOI及专有名词 token 不得变化。"""

import re

_TOKEN_PATTERN = re.compile(
    r"(?i)(?:\b(?:PMID|DOI)\s*[:：]?\s*[A-Za-z0-9./_-]+)|"
    r"(?:\d+(?:\.\d+)?%?)|(?:\b(?:[A-Z][A-Za-z0-9-]{2,}|[A-Z]{2,})\b)"
)


def extract_protected_tokens(text: str) -> list[str]:
    """按原文顺序提取 token，避免数字交换后仍被排序掩盖。"""
    return _TOKEN_PATTERN.findall(text)


def validate_polish(original: str, polished: str) -> list[str]:
    before = extract_protected_tokens(original)
    after = extract_protected_tokens(polished)
    if before != after:
        raise ValueError(f"protected tokens changed: before={before!r}, after={after!r}")
    return []
