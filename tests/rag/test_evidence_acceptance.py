from app.rag.schemas import EvidenceSet, NumericFact


def test_wp6_schema_defaults_are_backward_compatible() -> None:
    evidence = EvidenceSet()
    assert evidence.status == "ready" and evidence.numeric_facts == [] and evidence.conflicts == []


def test_wp6_numeric_fact_requires_traceable_fields() -> None:
    fact = NumericFact(metric="PFS", value="12", unit="months", population="adults", source_chunk_id="c1")
    assert fact.verified is False
