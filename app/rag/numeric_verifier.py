"""Deterministic numeric-fact validation; never infers missing medical facts."""

from app.rag.schemas import NumericFact


def verified_numeric_facts(facts: list[NumericFact], evidence_chunk_ids: set[str]) -> list[NumericFact]:
    """Return only complete facts whose cited chunk is present and verified."""
    return [fact for fact in facts if fact.verified and fact.source_chunk_id in evidence_chunk_ids and all((fact.metric.strip(), fact.value.strip(), fact.unit.strip(), fact.population.strip()))]
