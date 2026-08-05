"""literature_search — 阅读顺序规则分类器（R2-WP08）。

review-paper 融合点：默认层级对应证据金字塔——综述（汇总证据）→ 指南/共识
（临床决策）→ 原始研究（一手证据）→ 前沿（时间信号）→ 高相关（用户问题）。
分类依据 CitationItem.publication_types 真实字段（EFetch PublicationType），
禁止猜测类型、禁止编造影响因子/被引量（延续 WP05 已确立的信号边界）。

search-lit 融合点：相关度信号只用 WP05 已有的 verified 与 PMID 检索顺序
（列表位置），不引入被引量等不可得数据。

本模块只包含纯函数：输入 CitationItem + 上下文，输出分类结果、证据特征与
规则理由；不触碰数据库、不调用模型。模型解释辅助由 service.py 编排，且
模型输出不得改变本模块的规则分类结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.modules.literature_search.schema import CitationItem

ReadingCategory = Literal[
    "review", "guideline", "original_research", "frontier", "highly_relevant"
]

# 证据金字塔层级：数值越小越先读。
_CATEGORY_ORDER: dict[ReadingCategory, int] = {
    "review": 0,
    "guideline": 1,
    "original_research": 2,
    "frontier": 3,
    "highly_relevant": 4,
}

# "近年前沿"的时间跨度：与 WP05 classic 排序的近 5 年信号保持一致。
_FRONTIER_YEAR_SPAN = 5

# 指南/共识类型关键词（子串匹配 EFetch 真实 PublicationType 值，如
# "Practice Guideline" / "Consensus Development Conference"）。
_GUIDELINE_KEYWORDS = ("guideline", "consensus")

# 综述/系统综述/荟萃分析关键词。
_REVIEW_KEYWORDS = ("review", "meta-analysis")

# 一手原始研究类型关键词。不含 "Journal Article"：它是 PubMed 默认类型，
# 几乎所有文章都带该标记，不能作为"一手研究"的判据。
_ORIGINAL_RESEARCH_KEYWORDS = (
    "clinical trial",
    "randomized",
    "comparative study",
    "observational study",
    "case report",
    "cohort",
    "multicenter study",
    "controlled clinical trial",
)


@dataclass(frozen=True)
class ReadingContext:
    """规则分类所需的真实上下文（全由调用方从快照与用户态读出）。

    position 为条目在检索结果快照中的 0-based 下标（PubMed 返回顺序即
    本次检索内的天然相关度信号）；fulltext_status 为 WP07 library_item 的
    全文状态（None 表示该文献尚未存入本地知识库）。
    """

    current_year: int
    position: int
    total_items: int
    fulltext_status: str | None = None


@dataclass(frozen=True)
class ClassifiedReadingItem:
    """一条文献的规则分类结果：类别、触发分类的真实特征与规则理由。

    year 独立冗余用于排序（None 表示年份未知，硬排到有年份条目之后，
    延续 WP05 ranking 对缺失年份的处理）；reason 由规则生成，保证无模型
    时也能给出可解释推荐。
    """

    pmid: str
    category: ReadingCategory
    evidence_features: tuple[str, ...]
    reason: str
    position: int
    year: int | None


def _has_any_keyword(publication_types: list[str], keywords: tuple[str, ...]) -> bool:
    """任一文献类型含任一关键词（不区分大小写子串匹配）。

    与 filtering._matches_publication_type 的匹配语义保持一致，保证筛选与
    阅读顺序分类对同一批类型字段的判定不打架。
    """
    lowered_types = [value.lower() for value in publication_types]
    return any(
        keyword in type_value
        for type_value in lowered_types
        for keyword in keywords
    )


def _matched_types(publication_types: list[str], keywords: tuple[str, ...]) -> list[str]:
    """返回命中的真实 PublicationType 值（原样，作为证据特征展示）。"""
    return [
        value
        for value in publication_types
        if any(keyword in value.lower() for keyword in keywords)
    ]


def _fulltext_note(context: ReadingContext) -> str:
    """全文状态说明：只描述真实信号，不做任何抓取或推断。"""
    if context.fulltext_status is None:
        return "全文状态：未在本地知识库（仅检索元数据）。"
    return f"全文状态：{context.fulltext_status}。"


def _build_reason(
    label: str,
    advice: str,
    method_note: str,
    uncertainty: str,
    item: CitationItem,
    context: ReadingContext,
    matched_types: list[str] | None = None,
) -> str:
    """组装人类可读解释：为什么推荐 + 先读/后读 + 背景/方法/前沿 +
    相关性 + 全文状态 + 不确定性。所有事实来自真实字段，绝不编造。
    """
    type_note = ""
    if matched_types:
        type_note = f"（命中类型 {', '.join(matched_types)}）"
    year_note = f"年份：{item.year}。" if item.year is not None else "年份：未知。"
    relevance = (
        f"相关度：本次检索内 PubMed 返回序第 {context.position + 1}"
        f"/{context.total_items}，经 PubMed 验证。"
        if item.verified
        else (
            f"相关度：本次检索内 PubMed 返回序第 {context.position + 1}"
            f"/{context.total_items}，未经验证。"
        )
    )
    return (
        f"{label}：{advice}{type_note}{year_note}{method_note}{relevance}"
        f"{_fulltext_note(context)}不确定性：{uncertainty}"
    )


def classify_reading_item(
    item: CitationItem, context: ReadingContext
) -> ClassifiedReadingItem:
    """把单条文献分类到证据金字塔层级，并返回可解释证据特征与规则理由。

    判定顺序对应金字塔优先级：指南/共识 → 综述 → 原始研究 → 前沿（年份
    信号）→ 高相关（兜底，相关度信号）。

    设计说明：
    - 优先级高的类别先判定：一篇同时含 Guideline 与 Review 类型的罕见条目
      归为指南（临床决策信号更具体）。
    - 年份缺失（None）的条目不进入前沿判定（无法证明"近年"），归兜底。
    - 最新 ≠ 最好：frontier 只表示时间信号，reason 中明确说明不视为质量
      高于旧研究。
    - evidence_features 只收录真实字段触发的特征（类型值 / 年份 / verified /
      检索位置），不包含被引量、影响因子等不可得数据。
    """
    types = item.publication_types
    features: list[str] = []
    if item.verified:
        features.append("verified=true")
    features.append(f"position={context.position}")
    if item.year is not None:
        features.append(f"year={item.year}")

    if _has_any_keyword(types, _GUIDELINE_KEYWORDS):
        matched = _matched_types(types, _GUIDELINE_KEYWORDS)
        features.append(f"publication_type={matched[0]}")
        return ClassifiedReadingItem(
            pmid=item.pmid,
            category="guideline",
            evidence_features=tuple(features),
            reason=_build_reason(
                label="指南或共识",
                advice="建议在综述之后、原始研究之前阅读，用于掌握临床决策标准。",
                method_note="指南/共识整合证据形成决策建议，证据层级仅次于综述。",
                uncertainty="指南可能滞后于最新原始研究，且区域适用性需结合本地情况判断。",
                item=item,
                context=context,
                matched_types=matched,
            ),
            position=context.position,
            year=item.year,
        )

    if _has_any_keyword(types, _REVIEW_KEYWORDS):
        matched = _matched_types(types, _REVIEW_KEYWORDS)
        features.append(f"publication_type={matched[0]}")
        return ClassifiedReadingItem(
            pmid=item.pmid,
            category="review",
            evidence_features=tuple(features),
            reason=_build_reason(
                label="高质量综述",
                advice="建议最先阅读，用于建立领域证据全貌。",
                method_note="综述/系统综述/荟萃分析汇总已有证据，是证据金字塔顶端。",
                uncertainty="综述反映作者筛选后的证据，可能遗漏最新原始研究，需留意版本与检索日期。",
                item=item,
                context=context,
                matched_types=matched,
            ),
            position=context.position,
            year=item.year,
        )

    if _has_any_keyword(types, _ORIGINAL_RESEARCH_KEYWORDS):
        matched = _matched_types(types, _ORIGINAL_RESEARCH_KEYWORDS)
        features.append(f"publication_type={matched[0]}")
        return ClassifiedReadingItem(
            pmid=item.pmid,
            category="original_research",
            evidence_features=tuple(features),
            reason=_build_reason(
                label="代表性原始研究",
                advice="建议在综述与指南之后阅读，用于核验一手证据。",
                method_note="原始研究提供一手数据（试验/观察/病例），可检验综述中的结论。",
                uncertainty="单一原始研究受样本与设计限制，需结合其他研究综合判断。",
                item=item,
                context=context,
                matched_types=matched,
            ),
            position=context.position,
            year=item.year,
        )

    if item.year is not None and item.year >= context.current_year - _FRONTIER_YEAR_SPAN:
        features.append(f"frontier=recent_{_FRONTIER_YEAR_SPAN}年")
        return ClassifiedReadingItem(
            pmid=item.pmid,
            category="frontier",
            evidence_features=tuple(features),
            reason=_build_reason(
                label="近年前沿研究",
                advice="建议在原始研究之后阅读，了解时间信号上的新进展。",
                method_note="因发表年份较新被标记为前沿；年份是时间信号而非质量信号，不代表优于旧研究。",
                uncertainty="新研究可能尚未被广泛验证，证据成熟度有限。",
                item=item,
                context=context,
            ),
            position=context.position,
            year=item.year,
        )

    # 兜底：无明确文献类型且非近年发表。相关度只用检索序与 verified 信号，
    # 不使用被引量/影响因子（WP05 已确立的边界，延续）。
    return ClassifiedReadingItem(
        pmid=item.pmid,
        category="highly_relevant",
        evidence_features=tuple(features),
        reason=_build_reason(
            label="与用户问题高度相关研究",
            advice="建议最后阅读，作为问题相关候选补充。",
            method_note="未命中明确文献类型且非近年发表，因检索相关度靠前被归为高相关。",
            uncertainty="相关度仅基于检索顺序信号；未使用被引量/影响因子（不可得数据不编造）。",
            item=item,
            context=context,
        ),
        position=context.position,
        year=item.year,
    )


def _year_sort_key(entry: ClassifiedReadingItem) -> tuple[int, int, int]:
    """年份降序排序键：有年份的条目在前、年份大者在前，None 排最后。

    取负值配合默认升序，避免 reverse=True 把 position 次级键也倒排导致
    同级内顺序与直觉相反（延续 WP05 ranking 的稳定排序处理）。
    """
    return -(1 if entry.year is not None else 0), -(entry.year or 0), entry.position


def rank_reading_order(
    classified: list[ClassifiedReadingItem],
) -> list[ClassifiedReadingItem]:
    """按证据金字塔层级生成阅读顺序（返回新列表，不修改入参）。

    层级序：review → guideline → original_research → frontier → highly_relevant。
    同级内：review/guideline/frontier 按年份降序（更新的先读，覆盖新证据）；
    original_research/highly_relevant 按检索位置升序（相关度优先）。
    年份缺失的条目硬排在有年份条目之后。
    """
    grouped: dict[ReadingCategory, list[ClassifiedReadingItem]] = {
        category: [] for category in _CATEGORY_ORDER
    }
    for entry in classified:
        grouped[entry.category].append(entry)

    result: list[ClassifiedReadingItem] = []
    for category, _ in _CATEGORY_ORDER.items():
        group = grouped[category]
        if category in {"review", "guideline", "frontier"}:
            group.sort(key=_year_sort_key)
        else:
            group.sort(key=lambda entry: (entry.position, entry.pmid))
        result.extend(group)
    return result


def apply_manual_order(
    classified: list[ClassifiedReadingItem],
    manual_order: list[str] | tuple[str, ...],
) -> list[ClassifiedReadingItem]:
    """按用户保存的人工顺序覆盖算法顺序（manage-refs 融合）。

    设计说明：manual_order 保存用户拖拽后的完整 PMID 顺序；重新生成阅读
    顺序（重新分类）时人工顺序优先于算法顺序。若条目因检索更新而消失，
    缺失 PMID 被忽略；未在 manual_order 中的条目保留算法相对顺序追加到
    末尾。空 manual_order 表示用户未调整过，返回算法顺序本身。
    """
    if not manual_order:
        return list(classified)
    by_pmid = {entry.pmid: entry for entry in classified}
    result: list[ClassifiedReadingItem] = []
    seen: set[str] = set()
    for pmid in manual_order:
        entry = by_pmid.get(pmid)
        if entry is None or pmid in seen:
            continue
        result.append(entry)
        seen.add(pmid)
    result.extend(entry for entry in classified if entry.pmid not in seen)
    return result
