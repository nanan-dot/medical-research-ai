import json

from app.modules.evidence_matrix.model import MatrixCell
from app.modules.outline.outline_builder import build_outline


def test_proposal_marks_direction_as_candidate() -> None:
    cell = MatrixCell(
        matrix_id=1,
        document_id=1,
        field_key="results",
        cell_value="Observed result",
        sources=json.dumps([{"pmid": "12345", "locator": "abstract"}]),
        status="generated",
    )
    claims = build_outline("proposal", [cell], ["Question"])
    assert claims[0].evidence[0].pmid == "12345"
    assert claims[-1].status == "candidate"
