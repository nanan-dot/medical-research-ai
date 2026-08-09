"""Pure assembly of outlines from matrix values only."""

import json
from app.modules.outline.schema import OutlineClaim, OutlineKind, OutlineSection
from app.modules.evidence_matrix.model import MatrixCell

FORBIDDEN = ("将证明", "已证实", "必然")


def build_outline(
    kind: OutlineKind, cells: list[MatrixCell], candidates: list[str]
) -> list[OutlineSection]:
    claims = [
        OutlineClaim(
            text=cell.cell_value,
            evidence=[item for item in _sources(cell.sources)],
            missing_evidence=not bool(json.loads(cell.sources)),
        )
        for cell in cells
        if cell.cell_value
    ]
    if any(word in claim.text for claim in claims for word in FORBIDDEN):
        raise ValueError("Outline contains prohibited factual candidate wording")
    titles = (
        ["背景", "主题分类", "主要机制", "研究证据", "争议", "局限", "未来方向"]
        if kind == "review"
        else [
            "问题重要性",
            "研究现状",
            "当前不足",
            "候选科学问题",
            "初步方法",
            "可行性",
            "需要导师确认",
        ]
    )
    sections = [OutlineSection(title=title, claims=[]) for title in titles]
    # 事实内容只能来自矩阵单元格；空节保持为空，避免为凑结构伪造陈述。
    sections[3 if kind == "review" else 1].claims.extend(claims)
    if kind == "proposal":
        sections[3].claims.extend(
            OutlineClaim(
                text=f"候选方向：拟研究 {name}",
                status="candidate",
                missing_evidence=True,
            )
            for name in candidates
        )
    return sections


def _sources(raw: str):
    from app.modules.comparison.shared import SourceRef

    return [SourceRef.model_validate(item) for item in json.loads(raw)]
