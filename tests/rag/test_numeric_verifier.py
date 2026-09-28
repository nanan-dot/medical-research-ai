from app.rag.numeric_verifier import verified_numeric_facts
from app.rag.schemas import NumericFact


def test_wp6_unverified_or_untraced_numbers_are_excluded() -> None:
    facts = [NumericFact(metric="PFS", value="12", unit="months", population="adults", source_chunk_id="c1", verified=False), NumericFact(metric="OS", value="20", unit="months", population="adults", source_chunk_id="c2", verified=True)]
    assert verified_numeric_facts(facts, {"c1"}) == []
