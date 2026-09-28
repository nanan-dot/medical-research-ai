"""Pure local fallback ordering for immutable PubMed snapshots."""

from __future__ import annotations

from app.modules.literature_search.schema import (
    CitationItem,
    RankedCitationItem,
    ResultQueryParams,
)

# custom 排序中"未配置自定义序号"的占位值：用超大值而非 0，避免与真实序号 0
# 混淆，使未排序条目稳定排在已排序条目之后。
_NO_CUSTOM_ORDER = 2**31


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
