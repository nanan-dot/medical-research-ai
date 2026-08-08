"""从手稿文本提取引用标识符。

当前实现为规则/正则方式（标注实现方式：正则，非 ML），不做语义理解：
- PMID：形如 PMID: 12345678 或 PubMed ID 12345678；
- DOI：标准 10.xxxx/yyyy 形态。
提取结果去重并保留原始片段，供 verifier 校验真实性。
"""

from __future__ import annotations

import re

from app.modules.citation_check.schema import CitationAuditItem, CitationKind

# PMID 长度 1-8 位数字，通常跟随 "PMID" / "PubMed ID" / "pubmed" 标签。
_PMID_PATTERN = re.compile(r"(?:PMID|PubMed\s+ID|pubmed)[:\s#]*(\d+)", re.IGNORECASE)
# DOI 必须形如 10.<注册机构>/<后缀>，避免匹配普通数字或版本号。
# 后缀排除空白与常见句读标点（含 CJK 句号），防止把句子结尾标点吞入 DOI；
# 末尾不用 \b（词边界会因句子结尾的句点导致整条漏检），改由 strip 剥离尾部标点。
_DOI_PATTERN = re.compile(
    r"\b(10\.(?:\d{4,9}/[^\s,;:!?。，；：！？\"'<>]*|\d{0,3}(?!\d)))"
)

_MAX_RAW_PREFIX = 40


def extract_references(text: str) -> list[CitationAuditItem]:
    """从文本提取 PMID/DOI 引用，去重后返回待校验条目。

    设计说明：以 (kind, normalized_identifier) 为去重键，同一标识符重复出现
    只保留一次；原始片段保留该标识符首次出现处的前缀，便于用户在审计结果中
    定位。规范化：PMID 去掉前导零外的空白，DOI 转小写（DOI 大小写不敏感）。
    """
    items: list[CitationAuditItem] = []
    seen: set[tuple[CitationKind, str]] = set()

    for match in _PMID_PATTERN.finditer(text):
        identifier = match.group(1)
        key: tuple[CitationKind, str] = ("pmid", identifier)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            CitationAuditItem(
                raw=_raw_snippet(text, match.start()),
                kind="pmid",
                identifier=identifier,
                verified=False,
            )
        )

    for match in _DOI_PATTERN.finditer(text):
        identifier = match.group(1).strip(".,;")
        doi_key: tuple[CitationKind, str] = ("doi", identifier.lower())
        if doi_key in seen:
            continue
        seen.add(doi_key)
        items.append(
            CitationAuditItem(
                raw=_raw_snippet(text, match.start()),
                kind="doi",
                identifier=identifier,
                verified=False,
            )
        )

    return items


def _raw_snippet(text: str, position: int) -> str:
    """返回标识符出现处的前缀片段（最多 _MAX_RAW_PREFIX 字符）。"""
    start = max(0, position - _MAX_RAW_PREFIX)
    return text[start:position].strip()
