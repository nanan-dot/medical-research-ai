"""引用 L3 元数据一致性核验。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsistencyResult:
    status: str
    differences: list[str]


def compare_metadata(
    local: dict[str, object], remote: dict[str, object]
) -> ConsistencyResult:
    differences: list[str] = []
    local_title = str(local.get("title", "")).lower()
    remote_title = str(remote.get("title", "")).lower()
    if local_title and remote_title and not _title_overlap(local_title, remote_title):
        differences.append("title mismatch")
    local_authors = _author_names(local.get("authors"))
    remote_authors = _author_names(remote.get("authors"))
    if (
        local_authors
        and remote_authors
        and not local_authors.intersection(remote_authors)
    ):
        differences.append("authors mismatch")
    if local.get("year") and remote.get("year") and local["year"] != remote["year"]:
        differences.append("year mismatch")
    return ConsistencyResult("mismatch" if differences else "ok", differences)


def _title_overlap(left: str, right: str) -> bool:
    left_words = {word for word in left.split() if len(word) > 2}
    right_words = {word for word in right.split() if len(word) > 2}
    return bool(left_words.intersection(right_words))


def _author_names(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).lower() for item in value}
