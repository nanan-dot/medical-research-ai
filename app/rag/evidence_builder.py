"""Conservative, deterministic EvidenceSet construction."""

from app.rag.numeric_verifier import verified_numeric_facts
from app.rag.schemas import (
    EvidenceConflict,
    EvidenceSet,
    NumericFact,
    QueryPlan,
    RankedEvidence,
)


def build_evidence_set(plan: QueryPlan, evidence: list[RankedEvidence], facts: list[NumericFact]) -> EvidenceSet:
    required = {item.value.casefold() for item in plan.constraints if item.status == "required"}
    selected: list[RankedEvidence] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence:
        key = (item.document_id, " ".join(item.text_original.casefold().split()))
        if key in seen:
            continue
        seen.add(key)
        text = item.text_original.casefold()
        is_direct = bool(required) and all(value in text for value in required)
        selected.append(item.model_copy(update={"role": "direct" if is_direct else "context"}))
    direct = [item for item in selected if item.role == "direct"]
    valid_facts = verified_numeric_facts(facts, {item.chunk_id for item in selected})
    grouped: dict[tuple[str, str, str], list[NumericFact]] = {}
    for fact in valid_facts:
        grouped.setdefault((fact.metric, fact.unit, fact.population), []).append(fact)
    conflicts = [EvidenceConflict(metric=key[0], population=key[2], source_chunk_ids=[fact.source_chunk_id for fact in group]) for key, group in grouped.items() if len({fact.value for fact in group}) > 1]
    return EvidenceSet(evidence=selected, numeric_facts=valid_facts, conflicts=conflicts, status="ready" if direct else "insufficient_evidence")
