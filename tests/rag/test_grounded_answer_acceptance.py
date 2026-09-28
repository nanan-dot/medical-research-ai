from app.rag.schemas import GroundedAnswer, GroundedCitation, GroundedClaim


def test_wp7_grounded_answer_preserves_missing_page_and_compatibility_defaults() -> None:
    answer = GroundedAnswer(answer="x", claims=[GroundedClaim(claim="x", citation_ids=["c1"])], citations=[GroundedCitation(citation_id="c1", document_id="d1", chunk_id="k1", source_path="a")])
    assert answer.citations[0].page_number is None and answer.fallback is False
