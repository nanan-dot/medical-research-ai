"""候选方向生成结果的纯函数校验与同质化去重。"""

import re
from difflib import SequenceMatcher

from app.modules.comparison.shared import SourceRef
from app.modules.research_direction.schema import CandidateCore

SIMILARITY_THRESHOLD = 0.82


def parse_candidates(raw_response: str, allowed_sources: set[tuple[str | None, str | None, str]]) -> list[CandidateCore]:
    """解析模型 JSON，并拒绝未出现在矩阵中的来源。"""
    import json

    candidates = [CandidateCore.model_validate(item) for item in json.loads(raw_response)]
    for candidate in candidates:
        for evidence in candidate.evidence:
            _validate_source(evidence.source, allowed_sources)
        for source in [*candidate.current_evidence.sources, *candidate.controversy.sources]:
            _validate_source(source, allowed_sources)
    return deduplicate_candidates(candidates)


def deduplicate_candidates(candidates: list[CandidateCore]) -> list[CandidateCore]:
    """按归一化名称删除同质候选，避免多个“缺口法”只是换词。"""
    unique: list[CandidateCore] = []
    for candidate in candidates:
        normalized = _normalize_name(candidate.name)
        if any(_similarity(normalized, _normalize_name(item.name)) >= SIMILARITY_THRESHOLD for item in unique):
            continue
        unique.append(candidate)
    return unique


def _validate_source(source: SourceRef, allowed_sources: set[tuple[str | None, str | None, str]]) -> None:
    key = (source.pmid, source.doi, source.locator)
    if key not in allowed_sources:
        raise ValueError("Candidate evidence source is not present in the evidence matrix")


def _normalize_name(name: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", name).lower()


def _similarity(first: str, second: str) -> float:
    return SequenceMatcher(a=first, b=second).ratio()
