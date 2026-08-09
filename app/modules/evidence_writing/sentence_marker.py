"""句子级来源标记校验，不生成或改写医学内容。"""

from typing import Any

ALLOWED_ORIGINS = {
    "user_provided",
    "paper_evidence",
    "model_summary",
    "model_inference",
    "pending",
}


def validate_segments(
    segments: list[dict[str, Any]], *, pending_item_ids: set[str]
) -> list[dict[str, Any]]:
    if not segments:
        raise ValueError("Draft must contain marked content segments")
    for segment in segments:
        origin = segment.get("origin")
        if origin not in ALLOWED_ORIGINS or not segment.get("text"):
            raise ValueError("Every sentence must have text and a valid origin")
        citations = segment.get("citation_ids", [])
        if origin == "paper_evidence" and not citations:
            raise ValueError("paper_evidence requires citation_ids")
        if (
            origin == "pending"
            and segment.get("pending_item_id") not in pending_item_ids
        ):
            raise ValueError("pending sentence requires a matching pending item")
    return segments
