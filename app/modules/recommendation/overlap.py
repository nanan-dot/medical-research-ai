"""Conservative exact overlap classification for recommendation candidates."""

import re
from dataclasses import dataclass

from app.modules.literature_search.dedup import normalize_title

OVERLAP_PRIORITY = (
    "in_source_result",
    "in_reading_plan",
    "in_library",
    "in_knowledge_base",
    "near_duplicate",
)


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    return (
        re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value.strip().lower())
        or None
    )


@dataclass(frozen=True)
class OverlapResult:
    status: str
    evidence: list[dict[str, str]]
    limitations: list[str]


def classify_overlap(
    *,
    pmid: str,
    doi: str | None,
    source_pmids: set[str],
    source_dois: set[str],
    reading_pmids: set[str],
    library_pmids: set[str],
    library_dois: set[str],
    knowledge_pmids: set[str],
    knowledge_dois: set[str],
    title: str | None = None,
    covered_titles: set[str] | None = None,
    near_duplicate_pmids: set[str] | None = None,
) -> OverlapResult:
    normalized = normalize_doi(doi)
    evidence: list[dict[str, str]] = []
    checks = (
        (
            "in_source_result",
            pmid in source_pmids or bool(normalized and normalized in source_dois),
        ),
        ("in_reading_plan", pmid in reading_pmids),
        (
            "in_library",
            pmid in library_pmids or bool(normalized and normalized in library_dois),
        ),
        (
            "in_knowledge_base",
            pmid in knowledge_pmids
            or bool(normalized and normalized in knowledge_dois),
        ),
        (
            "near_duplicate",
            bool(near_duplicate_pmids and pmid in near_duplicate_pmids)
            or bool(
                covered_titles
                and (normalized_title := normalize_title(title))
                and normalized_title in covered_titles
            ),
        ),
    )
    for collection, matched in checks:
        if matched:
            evidence.append(
                {
                    "collection": collection,
                    "match": (
                        "normalized_title"
                        if collection == "near_duplicate"
                        else "pmid_or_normalized_doi"
                    ),
                }
            )
    status = next(
        (
            name
            for name in OVERLAP_PRIORITY
            if any(item["collection"] == name for item in evidence)
        ),
        "novel",
    )
    limitations = [] if covered_titles is not None else ["near_duplicate_unavailable"]
    return OverlapResult(status, evidence, limitations)
