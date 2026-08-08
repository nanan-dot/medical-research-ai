"""Pure assembly of outlines from matrix values only."""

import json
from app.modules.outline.schema import OutlineClaim, OutlineKind
from app.modules.evidence_matrix.model import MatrixCell

FORBIDDEN = ("将证明", "已证实", "必然")


def build_outline(
    kind: OutlineKind, cells: list[MatrixCell], candidates: list[str]
) -> list[OutlineClaim]:
    claims = [
        OutlineClaim(
            text=cell.cell_value,
            evidence=[item for item in _sources(cell.sources)],
            missing_evidence=not bool(json.loads(cell.sources)),
        )
        for cell in cells
        if cell.cell_value
    ]
    if kind == "proposal":
        claims.extend(
            OutlineClaim(text=f"候选方向：拟研究 {name}", status="candidate") for name in candidates
        )
    if any(word in claim.text for claim in claims for word in FORBIDDEN):
        raise ValueError("Outline contains prohibited factual candidate wording")
    return claims


def _sources(raw: str):
    from app.modules.comparison.shared import SourceRef

    return [SourceRef.model_validate(item) for item in json.loads(raw)]
