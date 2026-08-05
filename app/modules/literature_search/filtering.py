"""literature_search — 白名单筛选参数与内存过滤逻辑。

职责：把 ResultQueryParams（白名单校验已在 Pydantic 层完成，非法值返回
422）翻译为一组对 CitationItem 列表的谓词，逐个应用到快照条目。

设计说明：items_json 是已落库的检索快照（不可写回），因此筛选在服务端
对快照做内存过滤，而不是走 SQL。条目数上限为 retmax（默认 20，最大 500），
内存过滤量级可控，无需引入索引。用户态（saved/read/tags）通过
state_by_pmid 回调按 PMID 查询，本模块不感知用户态存储结构。
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.literature_search.schema import CitationItem, ResultQueryParams

# 用户态查询回调签名：pmid -> (saved, read_status, tags)。
UserStateLookup = Callable[[str], tuple[bool, str, list[str]]]


def _normalize_text(value: str | None) -> str:
    """文本归一化：小写 + 压缩空白。

    PubMed 中期刊名写法不统一（如 "Nat Med" 与 "Nature Medicine"），统一
    小写并压缩空白，让前端自由输入的期刊子串能命中不同大小写变体。
    """
    if not value:
        return ""
    return " ".join(value.lower().split())


def _matches_journal(journal: str | None, needle: str) -> bool:
    """期刊不区分大小写子串匹配。

    设计说明：不要求精确匹配，避免用户输入 "Nature Medicine" 而快照存的是
    "Nat Med" 时漏配（来源需求明确"期刊名称不统一"为必须处理的异常）。
    """
    return _normalize_text(needle) in _normalize_text(journal)


def _matches_publication_type(publication_types: list[str], needle: str) -> bool:
    """文献类型不区分大小写包含匹配。

    EFetch 的 PublicationType 常为完整短语（如 "Journal Article"），用户
    输入完整短语或子串（如 "Meta-Analysis"）均能命中。
    """
    lowered = needle.lower()
    return any(lowered in value.lower() for value in publication_types)


def _matches_author(authors: list[str], needle: str) -> bool:
    """作者子串包含匹配：输入姓或姓+首字母均能命中。"""
    lowered = _normalize_text(needle)
    return any(lowered in _normalize_text(author) for author in authors)


def _tags_contain(tags: list[str], needle: str) -> bool:
    """标签包含匹配：不区分大小写子串匹配，用于前端自由输入过滤。"""
    lowered = needle.lower()
    return any(lowered in tag.lower() for tag in tags)


def apply_filters(
    items: list[CitationItem],
    params: ResultQueryParams,
    *,
    state_by_pmid: UserStateLookup,
) -> list[CitationItem]:
    """按白名单筛选参数过滤条目，返回符合条件的子集（新列表）。

    用户态筛选（saved / read_status / tags）通过 state_by_pmid 实时查询；
    其余字段直接读条目快照字段。
    """

    def passes(item: CitationItem) -> bool:
        if params.year is not None and item.year != params.year:
            return False
        if params.publication_type is not None and not _matches_publication_type(
            item.publication_types, params.publication_type
        ):
            return False
        if params.journal is not None and not _matches_journal(item.journal, params.journal):
            return False
        if params.author is not None and not _matches_author(item.authors, params.author):
            return False
        # has_abstract 用真值判断而非 is：False 与 None 在旧快照中含义一致
        # （未知即视为无摘要），避免 None 永远无法匹配 has_abstract=false。
        if params.has_abstract is not None and bool(item.has_abstract) is not params.has_abstract:
            return False
        saved, read_status, tags = state_by_pmid(item.pmid)
        if params.saved is not None and saved is not params.saved:
            return False
        if params.read_status is not None and read_status != params.read_status:
            return False
        if params.tags is not None and not _tags_contain(tags, params.tags):
            return False
        return True

    # 列表推导生成新列表，避免在遍历原列表时删除元素导致跳过条目。
    return [item for item in items if passes(item)]
