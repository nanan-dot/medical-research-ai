from app.rag.schemas import RetrievalCandidate, RetrievalResult, to_ranked_evidence


def test_wp3_schema_preserves_evidence_identity_and_missing_page() -> None:
    candidate = RetrievalCandidate(document_id="d1", chunk_id="c1", source_path="a.pdf", heading="H", text_original="original")
    assert candidate.page_number is None and candidate.text_original == "original"


def test_wp3_legacy_result_has_explicit_ranked_evidence_adapter() -> None:
    result = RetrievalResult(text="original", source_path="a.pdf", heading="H", chunk_id="c1", raw_score=1.0, rank=2)
    evidence = to_ranked_evidence(result, document_id="d1", section="Results", page_number=None, index_version="v1")
    assert (evidence.document_id, evidence.chunk_id, evidence.page_number, evidence.text_original) == ("d1", "c1", None, "original")
