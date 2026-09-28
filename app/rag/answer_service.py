"""EvidenceSet-only generation boundary; no external model is selected here."""

from typing import Protocol

from app.rag.citation_mapper import map_citations
from app.rag.exceptions import GroundedGenerationError, InvalidGeneratedAnswerError
from app.rag.schemas import EvidenceSet, GroundedAnswer


class Generator(Protocol):
    model_version: str
    def generate(self, evidence: EvidenceSet) -> str: ...


def generate_answer(evidence: EvidenceSet, generator: Generator | None) -> GroundedAnswer:
    if evidence.status == "insufficient_evidence":
        return GroundedAnswer(answer="证据不足，无法生成确定答案。", evidence_status="insufficient_evidence", fallback=True)
    if generator is None:
        return GroundedAnswer(answer="生成器不可用。", evidence_status="system_failure", fallback=True)
    try:
        answer = GroundedAnswer(answer=generator.generate(evidence), citations=map_citations(evidence.evidence), limitations=["存在冲突证据，需人工核验"] if evidence.conflicts else [], model_version=generator.model_version)
        _validate_answer(answer, evidence)
        return answer
    except (GroundedGenerationError, ValueError):
        return GroundedAnswer(answer="生成器暂时失败。", evidence_status="system_failure", fallback=True)


def _validate_answer(answer: GroundedAnswer, evidence: EvidenceSet) -> None:
    citation_ids = {item.citation_id for item in answer.citations}
    valid_chunks = {item.chunk_id for item in evidence.evidence}
    valid_facts = {fact.source_chunk_id for fact in evidence.numeric_facts if fact.verified}
    for claim in answer.claims:
        if not claim.citation_ids or not set(claim.citation_ids).issubset(citation_ids):
            raise InvalidGeneratedAnswerError("generated claim is missing a valid citation")
        if claim.is_numeric and (not claim.numeric_fact_ids or not set(claim.numeric_fact_ids).issubset(valid_facts)):
            raise InvalidGeneratedAnswerError("numeric claim lacks verified numeric facts")
    if not {item.chunk_id for item in answer.citations}.issubset(valid_chunks):
        raise InvalidGeneratedAnswerError("citation does not map to evidence")
