from app.rag.evidence_builder import build_evidence_set
from app.rag.schemas import Constraint, NumericFact, QueryPlan, RankedEvidence


def _evidence(chunk_id: str, text: str) -> RankedEvidence:
    return RankedEvidence(document_id="d1", chunk_id=chunk_id, source_path="a", text_original=text, rank=1)


def test_wp6_direct_requires_all_required_constraints() -> None:
    result = build_evidence_set(QueryPlan(query="q", constraints=[Constraint(field="drug", value="drug a", status="required"), Constraint(field="outcome", value="pfs", status="required")]), [_evidence("c1", "drug a improves pfs")], [])
    assert result.status == "ready" and result.evidence[0].role == "direct"


def test_wp6_unverified_numbers_and_different_populations_do_not_conflict() -> None:
    result = build_evidence_set(QueryPlan(query="q"), [_evidence("c1", "context")], [NumericFact(metric="PFS", value="10", unit="months", population="adults", source_chunk_id="c1", verified=True), NumericFact(metric="PFS", value="12", unit="months", population="children", source_chunk_id="c1", verified=True)])
    assert result.numeric_facts and result.conflicts == []
