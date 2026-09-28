"""Deterministic, snapshot-backed explanations for reading-plan placement."""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.modules.literature_search.schema import CitationItem

_WORDS = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}")
_ENGLISH_STOPWORDS = {
    "analysis", "article", "effect", "patients", "research", "study", "treatment",
}
_CHINESE_STOPWORDS = {"分析", "患者", "研究", "治疗", "文章", "结果", "影响"}
_STAGE_TEXT = {
    "overview": "综述定位：先建立研究主题、证据谱系与术语边界。",
    "clinical_decision": "临床决策定位：优先核对指南、共识或临床决策相关框架。",
    "primary_evidence": "原始证据定位：优先阅读可直接支撑研究问题的原始研究设计。",
    "frontier": "前沿定位：用于补足尚未归入综述、指南或主要研究类型的最新线索。",
}


def _terms(value: object) -> set[str]:
    if isinstance(value, str):
        terms: set[str] = set()
        for word in _WORDS.findall(value):
            normalized = word.casefold()
            if normalized.isascii():
                if normalized not in _ENGLISH_STOPWORDS:
                    terms.add(normalized)
                continue
            for size in range(2, min(6, len(normalized)) + 1):
                terms.update(
                    normalized[index : index + size]
                    for index in range(len(normalized) - size + 1)
                )
        return terms - _CHINESE_STOPWORDS
    if isinstance(value, dict):
        return set().union(*(_terms(item) for item in value.values())) if value else set()
    if isinstance(value, Iterable):
        return set().union(*(_terms(item) for item in value))
    return set()


def _best_shared_terms(article_terms: set[str], intent_terms: set[str]) -> list[str]:
    selected: list[str] = []
    for term in sorted(article_terms & intent_terms, key=lambda value: (-len(value), value)):
        if any(term in existing for existing in selected):
            continue
        selected.append(term)
        if len(selected) == 5:
            break
    return selected


def build_reading_reason(
    citation: CitationItem,
    *,
    stage: str,
    role: str,
    intent: dict[str, object] | None,
    prior_stage_types: set[str],
    has_score: bool,
    manual: bool = False,
) -> dict[str, object]:
    """Return only claims directly attributable to the persisted snapshot."""
    limitations = ["未获取受限全文；该理由不评估全文结论或偏倚风险。"]
    sources = ["当前阅读计划阶段", "PubMed 检索结果快照", "Publication Type"]
    stage_fit = [_STAGE_TEXT[stage]]
    if citation.publication_types:
        stage_fit.append("文献类型：" + "、".join(citation.publication_types[:3]) + "。")
    else:
        limitations.append("缺少 Publication Type，阶段定位仅使用现有快照排序信息。")
    matches: list[str] = []
    article_terms = _terms([citation.title or "", citation.abstract or "", citation.mesh_terms])
    intent_terms = _terms(intent or {})
    shared = _best_shared_terms(article_terms, intent_terms)
    if intent and shared:
        matches.append("与已确认研究意图的共同词项：" + "、".join(shared) + "。")
        sources.append("已确认 Research Intent")
    elif not intent:
        limitations.append("未找到已确认 Research Intent，未生成研究问题匹配判断。")
    else:
        limitations.append("已确认 Research Intent 与当前标题、摘要和 MeSH 未出现可核对的共同词项。")
    if citation.abstract:
        sources.append("PubMed 摘要")
    else:
        limitations.append("PubMed 摘要缺失，未依据摘要作医学内容判断。")
    if citation.mesh_terms:
        sources.append("MeSH")
    else:
        limitations.append("MeSH 缺失，主题匹配范围受限。")
    if has_score:
        sources.append("已持久化文章评分")
    else:
        limitations.append("未找到可用文章评分；缺失信号未按零分处理。")
    incremental = [
        "作为当前阶段的" + ("核心阅读项" if role == "core" else "候选阅读项") + "，补充该阶段的文献覆盖。"
    ]
    types = set(citation.publication_types)
    if types and not types.issubset(prior_stage_types):
        incremental.append("其文献类型与本阶段已选条目存在补充差异。")
    if manual:
        limitations.append("该条目由人工加入；系统未将人工选择解释为医学证据强度。")
    status = "partial" if limitations[1:] else "complete"
    headline = "本阶段优先阅读" if role == "core" else "本阶段候选阅读"
    narrative = stage_fit[0] + (matches[0] if matches else "依据现有快照信息安排阅读顺序。")
    return {
        "headline": headline,
        "narrative": narrative,
        "stage_fit": stage_fit,
        "research_question_matches": matches,
        "incremental_value": incremental,
        "evidence_sources": sources,
        "limitations": limitations,
        "generation_method": "deterministic",
        "status": status,
    }
