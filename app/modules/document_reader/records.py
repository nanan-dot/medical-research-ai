"""统一记录分类策略。"""


def classify_annotation(note: str | None) -> str:
    """冻结互斥分类，防止一个底层批注同时进入两类计数。"""
    return "annotation" if note is not None and note.strip() else "highlight"


def filter_record_items(
    records: list[dict[str, object]],
    *,
    record_type: str | None,
    section_id: int | None,
    query: str | None,
) -> list[dict[str, object]]:
    normalized_query = query.strip().casefold() if query else None
    return [
        item
        for item in records
        if (record_type is None or item.get("record_type") == record_type)
        and (section_id is None or item.get("section_id") == section_id)
        and (
            normalized_query is None
            or normalized_query in str(item.get("text", "")).casefold()
        )
    ]


def summarize_record_items(records: list[dict[str, object]]) -> dict[str, int]:
    counts = {"highlight": 0, "annotation": 0, "question": 0, "bookmark": 0}
    for item in records:
        record_type = str(item["record_type"])
        if record_type in counts:
            counts[record_type] += 1
    return counts
