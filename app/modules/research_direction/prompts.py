"""研究方向生成提示词；输出约束在服务端再次验证。"""

import json


def build_candidates_prompt(
    conditions: dict[str, object],
    evidence_context: list[dict[str, object]],
    candidate_count: int,
) -> str:
    """构建只允许引用给定来源的候选生成提示。"""
    return f"""你是医学研究方向辅助工具，不替用户决定正式课题。
基于下列研究条件和证据矩阵，返回严格 JSON 数组，生成 {candidate_count} 条候选。
每条必须含 name, question, research_object, study_type, evidence, current_evidence,
controversy, gap, novelty_uncertainty, priority, generation_strategy, missing_evidence。
evidence 为 [{{statement, source: {{pmid|doi, locator}}}}]；current_evidence 和 controversy
均为 {{text, sources: [{{pmid|doi, locator}}]}}。全部 source 只能取给定来源。
gap 必须包含“当前检索结果中较少见”，禁止“首次、首创、空白领域、没人做过、保证发表”。
混合 gap-based 与 cross-topic；数据允许时至少一条 cross-topic。无证据必须 missing_evidence=true。
研究条件：{json.dumps(conditions, ensure_ascii=False)}
证据矩阵：{json.dumps(evidence_context, ensure_ascii=False)}"""


def build_details_prompt(
    direction: dict[str, object], evidence_context: list[dict[str, object]]
) -> str:
    """构建按需详情提示，避免首次生成携带冗长字段。"""
    return f"""为以下候选研究方向返回严格 JSON 对象，字段为 methods, requirements, difficulty,
time_risk, resource_risk, ethics_risk, search_terms, advisor_questions。不得假设用户已有设备；
requirements 中必须明确“需确认”。search_terms 必须是带 [Title/Abstract] 的 PubMed 布尔检索片段。
不得添加矩阵之外的 PMID 或 DOI。
候选：{json.dumps(direction, ensure_ascii=False)}
证据矩阵：{json.dumps(evidence_context, ensure_ascii=False)}"""
