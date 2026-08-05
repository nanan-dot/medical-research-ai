"""BibTeX 序列化。

依据 search-lit skill 的引用管理规范：
- citation key 格式为 FirstAuthorLastName_Year_OneWord（如 Kim_2024_Validation）；
- 每条记录携带 verified / verified_by / verified_on 字段，以对齐反幻觉协议。

所有字段均来自调用方传入的 CitationItem（数据库真实数据），本模块不做任何
补全或推断；缺失字段输出为 None，绝不伪造元数据。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.modules.literature_search.schema import CitationItem

if TYPE_CHECKING:
    from collections.abc import Iterable

# 标题首词白名单：BibTeX key 只保留纯 ASCII 字母/数字词，忽略括号与空格。
_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")
_FALLBACK_WORD = "Ref"


def citation_key(item: CitationItem) -> str:
    """按 FirstAuthorLastName_Year_OneWord 生成 BibTeX key。

    设计说明：OneWord 取标题第一个 ASCII 单词，避免中文标题进入 key；无标题或
    无 ASCII 词时退化为 Ref。作者缺失时用 Unknown 占位，年份缺失用 n.d.。
    """
    first_author = item.authors[0] if item.authors else None
    last_name = _last_name(first_author) if first_author else "Unknown"
    year = str(item.year) if item.year is not None else "n.d."
    one_word = _first_title_word(item.title) if item.title else _FALLBACK_WORD
    return f"{last_name}_{year}_{one_word}"


def to_bibtex(items: Iterable[CitationItem]) -> str:
    """把条目列表序列化为完整 BibTeX 文本（每条约 6 行，末尾一个换行）。"""
    entries = [_format_entry(item) for item in items]
    return "\n".join(entries) + "\n"


def _format_entry(item: CitationItem) -> str:
    fields = [
        ("author", _join_authors(item.authors)),
        ("title", item.title),
        ("journal", item.journal),
        ("year", item.year),
        ("doi", item.doi),
        ("pmid", item.pmid),
        ("verified", "true" if item.verified else "false"),
        ("verified_by", item.verified_by),
        ("verified_on", item.verified_on),
    ]
    body = ",\n".join(f"  {name} = {{{_escape(value)}}}" for name, value in fields)
    return f"@{item.entry_type}{{{citation_key(item)},\n{body}\n}}"


def _escape(value: str | int | None) -> str:
    """转义 BibTeX 特殊字符，返回空串表示 None。"""
    if value is None:
        return ""
    return (
        str(value)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
    )


def _last_name(author: str) -> str:
    """取作者姓氏，去掉非字母数字字符。

    设计说明：PubMed 作者格式统一为 "LastName FM"（姓在前、名首字母在后），
    因此取第一个词即姓氏；集体作者（如 "World Health Organization"）也返回
    第一个实词。若首个词异常为空，退化为取最后一个词。
    """
    parts = author.strip().split()
    if not parts:
        return "Unknown"
    candidate = parts[0]
    cleaned = re.sub(r"[^A-Za-z0-9]", "", candidate)
    if cleaned:
        return cleaned
    # 首个词纯符号（罕见），退化为最后一段
    last = parts[-1]
    return re.sub(r"[^A-Za-z0-9]", "", last) or "Unknown"


def _first_title_word(title: str) -> str:
    """返回标题第一个纯 ASCII 单词，找不到返回 Ref。"""
    match = _WORD_PATTERN.search(title)
    return match.group(0) if match else _FALLBACK_WORD


def _join_authors(authors: list[str]) -> str:
    """把作者列表拼接为 BibTeX author 字段（and 分隔）。"""
    return " and ".join(authors) if authors else ""
