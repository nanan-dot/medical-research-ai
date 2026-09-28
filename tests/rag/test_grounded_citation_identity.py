from app.rag.schemas import GroundedCitation


def test_wp7_domain_and_database_document_identity_are_separate() -> None:
    citation = GroundedCitation(citation_id="c", document_id="123", chunk_id="k", source_path="a")
    assert citation.document_id == "123" and citation.database_document_id is None


def test_wp7_explicit_database_identity_is_preserved() -> None:
    citation = GroundedCitation(citation_id="c", document_id="external-1", database_document_id=5, chunk_id="k", source_path="a")
    assert citation.database_document_id == 5
