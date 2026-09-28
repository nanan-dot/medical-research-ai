"""Versioned, missing-aware recommendation scoring rules."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from app.modules.literature_search.schema import CitationItem

Mode = Literal["balanced", "latest", "key_evidence"]
ALGORITHM_VERSION = "recommendation-v5.3"
FEATURE_SCHEMA_VERSION = "recommendation-features-v1"
MODE_WEIGHTS: dict[Mode, dict[str, float]] = {
    "balanced": {"relevance": 0.60, "incremental": 0.25, "evidence_fit": 0.15},
    "latest": {
        "relevance": 0.55,
        "incremental": 0.20,
        "evidence_fit": 0.10,
        "recency": 0.15,
    },
    "key_evidence": {
        "relevance": 0.50,
        "incremental": 0.20,
        "evidence_fit": 0.25,
        "open_signal": 0.05,
    },
}
MIN_RELEVANCE = 0.20


def weighted_available_score(
    values: dict[str, float | None], weights: dict[str, float]
) -> tuple[float | None, list[str]]:
    available = [
        (name, value, weights[name])
        for name, value in values.items()
        if value is not None and name in weights
    ]
    denominator = sum(weight for _, _, weight in available)
    if not available or denominator == 0:
        return None, []
    return round(
        sum(value * weight for _, value, weight in available) / denominator, 6
    ), [name for name, _, _ in available]


def priority_score(
    mode: Mode,
    *,
    relevance: float | None,
    incremental: float | None,
    evidence_fit: float | None,
    recency: float | None = None,
    open_signal: float | None = None,
) -> tuple[float | None, list[str]]:
    if relevance is not None and relevance < MIN_RELEVANCE:
        return None, ["below_minimum_relevance"]
    return weighted_available_score(
        {
            "relevance": relevance,
            "incremental": incremental,
            "evidence_fit": evidence_fit,
            "recency": recency,
            "open_signal": open_signal,
        },
        MODE_WEIGHTS[mode],
    )


def evidence_fit(
    question_type: str | None, publication_types: list[str]
) -> tuple[float | None, list[str]]:
    if not question_type or not publication_types:
        return None, []
    normalized = " ".join(publication_types).lower()
    preferred = {
        "treatment": (
            "meta-analysis",
            "systematic review",
            "randomized controlled trial",
        ),
        "diagnosis": ("diagnostic", "systematic review"),
        "prognosis": ("prospective", "cohort"),
        "etiology": ("cohort", "case-control"),
        "mechanism": ("basic research", "translational", "in vitro", "animal"),
    }.get(question_type.lower())
    if preferred is None:
        return None, []
    hits = [study_type for study_type in preferred if study_type in normalized]
    return ((1.0 if hits else 0.4), hits)


def recency_score(year: int | None, *, current_year: int | None = None) -> float | None:
    if year is None:
        return None
    age = max(0, (current_year or datetime.now(UTC).year) - year)
    return round(max(0.0, 1 - age / 10), 6)


def stable_rank(rows: list[tuple[str, float | None, int | None]]) -> list[str]:
    return [
        row[0]
        for row in sorted(
            rows,
            key=lambda row: (row[1] is None, -(row[1] or 0), -(row[2] or 0), row[0]),
        )
    ]


def select_ranked_novel_pmids(
    rows: list[tuple[str, float | None, int | None]], *, candidate_count: int
) -> list[str]:
    """Exclude ineligible rows, rank the full pool, then enforce the quota."""
    eligible = [row for row in rows if row[1] is not None]
    return stable_rank(eligible)[:candidate_count]


def intent_concept_coverage(
    items: list[CitationItem], dimensions: dict[str, object]
) -> dict[str, dict[str, int]]:
    """Count source-snapshot metadata coverage for each intent concept."""
    baseline: dict[str, dict[str, int]] = {}
    for dimension in (
        "population",
        "intervention",
        "comparison",
        "outcome",
        "target",
        "mechanism",
        "study_type",
    ):
        raw = dimensions.get(dimension)
        values = raw if isinstance(raw, list) else [raw] if isinstance(raw, str) else []
        concepts = [str(value).strip() for value in values if str(value).strip()]
        if not concepts:
            continue
        baseline[dimension] = {}
        for concept in concepts:
            baseline[dimension][concept] = sum(
                concept.casefold()
                in " ".join(
                    [
                        item.title or "",
                        item.abstract or "",
                        *item.mesh_terms,
                        *item.publication_types,
                    ]
                ).casefold()
                for item in items
            )
    return baseline


def openalex_signal(cited_by_count: int | None) -> float | None:
    """Bound optional impact without treating it as relevance evidence."""
    if cited_by_count is None:
        return None
    import math

    return round(min(1.0, math.log1p(max(0, cited_by_count)) / math.log(101)), 6)
