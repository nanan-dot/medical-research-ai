"""将推荐请求保守转换为 PubMed 检索式，不让模型决定候选文献。"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.literature_search.query_builder import build_boolean_query
from app.modules.literature_search.schema import BooleanQueryResult, SearchTermGroup
from app.modules.literature_search.term_expansion import expand_term

_MAX_QUERY_LENGTH = 1000
_UNSAFE_MARKERS = ("{", "}", ";", "\n", "\r")
_TERM_ALIASES = {
    "胃癌": ("disease", "gastric cancer"),
    "肺癌": ("disease", "lung cancer"),
    "乳腺癌": ("disease", "breast cancer"),
    "糖尿病": ("disease", "diabetes"),
    "阿尔茨海默病": ("disease", "alzheimer disease"),
    "免疫治疗": ("intervention", "immunotherapy"),
    "二甲双胍": ("intervention", "metformin"),
    "阿司匹林": ("intervention", "aspirin"),
    "靶向治疗": ("intervention", "targeted therapy"),
    "lung cancer": ("disease", "lung cancer"),
    "gastric cancer": ("disease", "gastric cancer"),
    "breast cancer": ("disease", "breast cancer"),
    "diabetes": ("disease", "diabetes"),
    "immunotherapy": ("intervention", "immunotherapy"),
    "metformin": ("intervention", "metformin"),
}


@dataclass(frozen=True)
class RecommendationQuery:
    """构造结果及可审计来源。"""

    boolean_query: str
    term_sources: dict[str, str]
    query_result: BooleanQueryResult


class RecommendationQueryBuilder:
    """仅使用本地已核对映射，不用 LLM 生成检索词。"""

    def build(self, request: str) -> RecommendationQuery:
        cleaned = " ".join(request.split())
        if not cleaned:
            raise ValueError("recommendation query must be non-empty")
        if len(cleaned) > _MAX_QUERY_LENGTH:
            raise ValueError("recommendation query must be at most 1000 characters")
        if any(marker in cleaned for marker in _UNSAFE_MARKERS):
            raise ValueError("recommendation query contains unsafe control characters")

        groups: dict[str, list[str]] = {}
        sources: dict[str, str] = {}
        lower = cleaned.casefold()
        for alias, (group_name, mapped_term) in sorted(
            _TERM_ALIASES.items(), key=lambda pair: -len(pair[0])
        ):
            if alias.casefold() not in lower:
                continue
            expansion = expand_term(mapped_term)
            terms = groups.setdefault(group_name, [])
            terms.extend((expansion.core_term, *expansion.synonyms))
            sources[group_name] = expansion.source

        if "综述" in cleaned or "review" in lower:
            groups.setdefault("study_type", []).append("Review")
            sources["study_type"] = "curated_pubmed_publication_type"

        if not groups:
            if not cleaned.isascii():
                raise ValueError("no safe curated mapping exists for this request")
            groups["topic"] = [cleaned]
            sources["topic"] = "user_supplied"

        term_groups = [
            SearchTermGroup(
                name=name,
                core_term=terms[0],
                terms=list(dict.fromkeys(terms)),
                field_tag="Publication Type"
                if name == "study_type"
                else "Title/Abstract",
                source=sources[name],
            )
            for name, terms in groups.items()
        ]
        query_result = build_boolean_query(term_groups)
        return RecommendationQuery(
            boolean_query=query_result.boolean_query,
            term_sources=sources,
            query_result=query_result,
        )
