"""跨服务的一致性策略。"""


def ensure_revision_fence(
    *, anchor_revision_id: int, segmentation_anchor_revision_id: int
) -> None:
    if anchor_revision_id != segmentation_anchor_revision_id:
        raise ValueError("segmentation revision does not derive from anchor revision")


def no_evidence_answer_status(source_anchor_ids: list[int]) -> str:
    return "answer" if source_anchor_ids else "no_answer"

