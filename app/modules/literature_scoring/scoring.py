"""Pure scoring primitives with explicit missing-data semantics."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

METRIC_AVAILABLE = "available"
METRIC_MISSING = "missing_input"
METRIC_HISTORY = "insufficient_history"


@dataclass(frozen=True)
class MetricValue:
    """A score never turns unavailable evidence into a synthetic zero."""

    score: float | None
    status: str
    reason: str | None = None


def weighted_score(parts: list[tuple[float, MetricValue]]) -> MetricValue:
    """Normalize only available components so absent sources do not penalize papers."""
    usable = [
        (weight, value.score)
        for weight, value in parts
        if value.status == METRIC_AVAILABLE and value.score is not None
    ]
    if not usable:
        return MetricValue(None, METRIC_MISSING, "no_scoring_inputs_available")
    denominator = sum(weight for weight, _ in usable)
    return MetricValue(
        round(sum(weight * score for weight, score in usable) / denominator, 2),
        METRIC_AVAILABLE,
    )


def recency_score(age_months: int | None, half_life_months: int = 30) -> MetricValue:
    """Compute a bounded, article-age signal without inferring publication dates."""
    if age_months is None:
        return MetricValue(None, METRIC_MISSING, "publication_date_unknown")
    return MetricValue(
        round(100 * exp(-log(2) * max(age_months, 0) / half_life_months), 2),
        METRIC_AVAILABLE,
    )


def popularity_from_yearly_counts(
    counts_by_year: dict[int, int] | None, current_year: int
) -> MetricValue:
    """Require annual history; cumulative citations alone cannot represent popularity."""
    if not counts_by_year or len(counts_by_year) < 2:
        return MetricValue(None, METRIC_HISTORY, "annual_citation_history_unavailable")
    recent = counts_by_year.get(current_year, 0) + counts_by_year.get(
        current_year - 1, 0
    )
    prior = counts_by_year.get(current_year - 2, 0) + counts_by_year.get(
        current_year - 3, 0
    )
    if recent + prior == 0:
        return MetricValue(0.0, METRIC_AVAILABLE)
    return MetricValue(round(100 * recent / (recent + prior), 2), METRIC_AVAILABLE)
