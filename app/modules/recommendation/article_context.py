"""仅从文献类型和题名提取研究设计线索，不将摘要中的背景研究当作本研究。"""

import re

from app.modules.literature_search.schema import CitationItem

_DESIGNS = (
    ("systematic review", "系统综述"),
    ("meta-analysis", "荟萃分析"),
    ("randomized controlled trial", "随机对照试验"),
    ("single-arm", "单臂研究"),
    ("post-marketing", "上市后监测"),
    ("retrospective", "回顾性研究"),
    ("prospective", "前瞻性研究"),
    ("case report", "病例报告"),
)


def study_design_matches(item: CitationItem) -> list[dict[str, object]]:
    """显式标注来自 PubMed 文献类型或题名的线索及原文。"""
    matches: list[dict[str, object]] = []
    for term, label in _DESIGNS:
        for field, text in (
            ("pubmed_publication_type", " ".join(item.publication_types)),
            ("pubmed_title", item.title or ""),
        ):
            if not re.search(r"(?<![\w-])" + re.escape(term) + r"s?(?!\w)", text, re.IGNORECASE):
                continue
            if term == "randomized controlled trial" and re.search(r"non[- ]randomized", text, re.IGNORECASE):
                continue
            source = "文献类型" if field == "pubmed_publication_type" else "题名"
            matches.append({
                "dimension": "study_type", "status": "matched", "matched_terms": [term],
                "source": "article_metadata", "field": field,
                "reason": f"{source}提供{label}线索", "version": "article-context-v1",
                "excerpt": text, "display_text": f"{source}提供{label}线索",
            })
            break
    return matches
