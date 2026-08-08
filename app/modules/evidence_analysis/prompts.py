"""Auditable prompt construction for grounded evidence interpretation."""

import json

from app.modules.evidence_analysis.schema import StatisticsLayerRead

PROMPT_VERSION = "r3-wp03-v1"


def build_interpretation_prompt(
    statistics: StatisticsLayerRead,
    source_catalog: list[dict[str, object]],
    evidence_context: list[dict[str, object]],
    retrieval_scope: str,
    retrieval_date: str,
) -> str:
    """Require source-bound, type-aware JSON instead of ungrounded topic claims."""
    statistics_json = statistics.model_dump_json()
    sources_json = json.dumps(source_catalog, ensure_ascii=False)
    return f"""You are interpreting a bounded medical-literature evidence matrix.
Return JSON only with consistencies, conflicts, limitations, gaps, and search_questions.
Every item must include statement, confidence (high/medium/low), evidence, statistics_basis, and research_types.
Conflicts must additionally include conflicting_point, supporting_evidence, opposing_evidence.
Search questions must additionally include question and executable PubMed-style search_fragment.
Use only identifiers in the source catalog. Cite at least one statistics_basis EXACTLY as supplied below.
Keep original studies and reviews distinct; do not treat their conclusions as equal evidence.
Statistics are clues, not conclusions. For gaps say only '当前检索结果中较少见' when justified; never say 没人做过, 空白领域, or 首次.
Retrieval scope: {retrieval_scope}
Retrieval date: {retrieval_date}
Statistics catalog: {statistics_json}
Source catalog: {sources_json}
Evidence context (including user notes when supplied): {json.dumps(evidence_context, ensure_ascii=False)}
"""
