"""Map only application-owned RankedEvidence into grounded citations."""

from app.rag.schemas import GroundedCitation, RankedEvidence


def map_citations(evidence: list[RankedEvidence]) -> list[GroundedCitation]:
    return [GroundedCitation(citation_id=item.chunk_id, document_id=item.document_id, chunk_id=item.chunk_id, source_path=item.source_path, page_number=item.page_number) for item in evidence]
