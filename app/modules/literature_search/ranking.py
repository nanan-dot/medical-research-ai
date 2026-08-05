"""literature_search — 相关性 / 最新 / 经典代表性 / 自定义排序。

search-lit 融合点：
- "经典代表性"（classic）排序：因 PubMed ESearch 不返回被引量，采用可解释的
  替代信号——权威期刊加权 + 年份权重 + verified 标记——并在每条结果的
  sort_reason 中说明理由。绝不编造被引次数或影响因子。
- 排序理由（sort_reason）：每个排序结果附带一条人类可读的解释（如
  "top journal + recent year"），前端可直接展示，对应反幻觉协议延伸。

稳定排序：所有排序都使用"主排序键 + pmid 次级键"保证同分时顺序确定，
避免翻页时结果在相邻页之间跳动。
"""

from __future__ import annotations

from app.modules.literature_search.schema import (
    CitationItem,
    RankedCitationItem,
    ResultQueryParams,
)

# 权威期刊白名单（小写比较）。这些是公认的高影响力期刊，作为"代表性"的
# 可解释替代信号；此处只表示期刊名称本身，不包含任何影响因子数字。
_TOP_JOURNALS = frozenset(
    {
        "nature",
        "science",
        "the new england journal of medicine",
        "lancet",
        "jama",
        "cell",
        "bmj",
        "annals of internal medicine",
        "nature medicine",
        "nature reviews cancer",
        "nature reviews clinical oncology",
        "nature reviews drug discovery",
        "nature reviews molecular cell biology",
    }
)

# 经典排序的年份权重：近 5 年 +1。年份缺失的条目不参与加权并排到最后。
_RECENT_YEAR_SPAN = 5

# 权威期刊加权分；verified 加成；最近年份加成。
_TOP_JOURNAL_SCORE = 2
_VERIFIED_SCORE = 1
_RECENT_YEAR_SCORE = 1

# custom 排序中"未配置自定义序号"的占位值：用超大值而非 0，避免与真实序号 0
# 混淆，使未排序条目稳定排在已排序条目之后。
_NO_CUSTOM_ORDER = 2**31


def _journal_key(journal: str | None) -> str:
    return " ".join((journal or "").lower().split())


def _rank_classic(item: CitationItem, current_year: int) -> tuple[int, int]:
    """经典代表性得分：(权威期刊加权 + verified + 最近年份, 年份)。

    设计说明：被引量在 PubMed 数据源中不可用，因此用三个可解释信号排序：
    权威期刊 +2、verified +1、近 5 年 +1。年份作为次级键使同一加权分内
    更新的文献靠前；年份缺失（None）排在最后（用 0 替代年份排序）。
    """
    score = 0
    if _journal_key(item.journal) in _TOP_JOURNALS:
        score += _TOP_JOURNAL_SCORE
    if item.verified:
        score += _VERIFIED_SCORE
    if item.year is not None and item.year >= current_year - _RECENT_YEAR_SPAN:
        score += _RECENT_YEAR_SCORE
    year_sort = item.year if item.year is not None else 0
    return score, year_sort


def _classic_sort_key(entry: RankedCitationItem, current_year: int) -> tuple[int, int, int, str]:
    """classic 排序键：有年份优先 → 加权分降序 → 年份降序 → pmid 升序。

    取负值配合默认升序，避免 reverse=True 把 pmid 次级键也倒排导致同分
    条目按 PMID 倒序，翻页时顺序与直觉相反。

    设计说明：年份缺失是硬规则——无论期刊多权威、verified 与否，None 年份
    一律排在有年份条目之后（对应"年份缺失"异常处理）。因此首键用
    -(有年份) 分组：有年份取 -1、缺失取 0，升序时缺失组自然落尾。
    """
    score, year_sort = _rank_classic(entry.item, current_year)
    has_year = 1 if entry.item.year is not None else 0
    return -has_year, -score, -year_sort, entry.item.pmid


def _classic_reason(item: CitationItem, current_year: int) -> str:
    """为 classic 排序生成可解释理由（只描述真实信号）。"""
    reasons: list[str] = []
    if _journal_key(item.journal) in _TOP_JOURNALS:
        reasons.append("top journal")
    if item.verified:
        reasons.append("verified by pubmed")
    if item.year is not None and item.year >= current_year - _RECENT_YEAR_SPAN:
        reasons.append("recent year")
    if item.year is None:
        reasons.append("year unknown")
    if not reasons:
        reasons.append("standard signal")
    return " + ".join(reasons)


def sort_items(
    items: list[CitationItem],
    params: ResultQueryParams,
    *,
    current_year: int,
    custom_order: dict[str, int] | None = None,
) -> list[RankedCitationItem]:
    """按 params.sort 排序并生成逐条排序理由。

    relevance 为 PubMed 返回顺序即天然相关性，不做重排，理由统一说明
    "相关性为本次检索内排序"，避免用户误以为可与跨检索结果比较。
    custom 使用 custom_order 中的用户自定义序号（缺省按 0 计），用于
    前端拖拽排序的持久化。

    稳定排序：所有排序路径都以 (排序键, pmid) 作为最终键，pmid 为字符串
    天然可比较，保证同分时顺序确定。
    """
    sort = params.sort
    if sort == "relevance":
        ranked = [
            RankedCitationItem(
                item=item,
                sort_reason="relevance: ordered by PubMed default ranking for this search",
            )
            for item in items
        ]
    elif sort == "newest":
        ranked = [
            RankedCitationItem(
                item=item,
                sort_reason="newest: sorted by publication year (descending)"
                if item.year is not None
                else "newest: year unknown (placed last)",
            )
            for item in items
        ]
        # 年份降序、pmid 升序兜底（年份用 0 替代使 None 排最后；负年份取负值
        # 避免 reverse=True 把 pmid 次级键倒排）。
        ranked.sort(
            key=lambda entry: (-(entry.item.year or 0), entry.item.pmid),
        )
    elif sort == "classic":
        ranked = [
            RankedCitationItem(
                item=item, sort_reason=_classic_reason(item, current_year)
            )
            for item in items
        ]
        # 主键：加权分降序；次级键：年份降序；pmid 升序兜底稳定同分。
        ranked.sort(key=lambda entry: _classic_sort_key(entry, current_year))
    elif sort == "custom":
        order = custom_order or {}
        ranked = [
            RankedCitationItem(
                item=item,
                sort_reason="custom: user-defined order (fallback to relevance order)",
            )
            for item in items
        ]
        # 已配置序号的条目按序号升序排在最前；未配置序号的条目保留原始相对
        # 顺序排在已配置条目之后。用 (序号, 原始下标) 作为键：有序号的条目
        # 先按序号排，无序号条目（序号为 None）用 inf 稳定排最后且保持输入
        # 相对顺序，避免跨页时未排序条目的顺序跳动。
        indexed = list(enumerate(ranked))
        indexed.sort(
            key=lambda pair: (
                order.get(pair[1].item.pmid, _NO_CUSTOM_ORDER),
                pair[0],
            )
        )
        ranked = [entry for _, entry in indexed]
    else:  # pragma: no cover - Literal 已约束，防御未知枚举。
        raise ValueError(f"unsupported sort: {sort}")

    return ranked
