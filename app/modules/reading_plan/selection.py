"""Deterministic, metadata-only reading-plan selection."""

from dataclasses import dataclass
from typing import Literal

Stage = Literal["overview", "clinical_decision", "primary_evidence", "frontier"]
Role = Literal["core", "candidate"]
STAGES: tuple[Stage, ...] = (
    "overview",
    "clinical_decision",
    "primary_evidence",
    "frontier",
)
BASE_QUOTAS: dict[Stage, int] = {
    "overview": 3,
    "clinical_decision": 2,
    "primary_evidence": 5,
    "frontier": 2,
}


@dataclass(frozen=True)
class SelectionCandidate:
    pmid: str
    position: int
    year: int | None
    publication_types: tuple[str, ...] = ()
    has_abstract: bool = False
    mesh_match_count: int = 0
    article_score: float | None = None
    recent_citations: int | None = None
    cited_by_count: int | None = None
    journal_metric: float | None = None


@dataclass(frozen=True)
class SelectedItem:
    pmid: str
    stage: Stage
    role: Role
    stage_order: int
    recommendation_reason: str
    evidence_features: dict[str, object]
    limitations: tuple[str, ...]


def classify_stage(candidate: SelectionCandidate) -> Stage:
    """Classify by study type first; recency is the truthful fallback signal."""
    types = " ".join(candidate.publication_types).lower()
    if "review" in types or "meta-analysis" in types:
        return "overview"
    if "guideline" in types or "consensus" in types:
        return "clinical_decision"
    primary_markers = (
        "randomized", "clinical trial", "cohort", "observational",
        "comparative study", "case-control", "multicenter",
    )
    if any(marker in types for marker in primary_markers):
        return "primary_evidence"
    return "frontier"


def _scaled_quotas(target: int) -> dict[Stage, int]:
    raw = {stage: target * value / 12 for stage, value in BASE_QUOTAS.items()}
    quotas = {stage: int(raw[stage]) for stage in STAGES}
    remainder = target - sum(quotas.values())
    priority = sorted(STAGES, key=lambda stage: (-(raw[stage] - quotas[stage]), STAGES.index(stage)))
    for stage in priority[:remainder]:
        quotas[stage] += 1
    return quotas


def allocate_core_quotas(
    candidates: list[SelectionCandidate], target_core_count: int
) -> dict[Stage, int]:
    """Allocate shortages deterministically in the fixed public stage order."""
    available = {stage: 0 for stage in STAGES}
    for candidate in candidates:
        available[classify_stage(candidate)] += 1
    desired = _scaled_quotas(target_core_count)
    quotas = {stage: min(desired[stage], available[stage]) for stage in STAGES}
    remaining = min(target_core_count, len(candidates)) - sum(quotas.values())
    while remaining:
        progressed = False
        for stage in STAGES:
            if quotas[stage] >= available[stage]:
                continue
            quotas[stage] += 1
            remaining -= 1
            progressed = True
            if not remaining:
                break
        if not progressed:
            break
    return quotas


def _score_key(candidate: SelectionCandidate) -> tuple[float, int, str]:
    """Rank available signals without treating missing observations as zero."""
    values: list[float] = [1 / (candidate.position + 1)]
    if candidate.has_abstract:
        values.append(0.15)
    if candidate.mesh_match_count:
        values.append(min(candidate.mesh_match_count, 5) * 0.04)
    if candidate.article_score is not None:
        values.append(candidate.article_score * 0.20)
    if candidate.recent_citations is not None:
        values.append(min(candidate.recent_citations, 100) / 100 * 0.10)
    if candidate.journal_metric is not None:
        values.append(min(candidate.journal_metric, 50) / 50 * 0.04)
    return (-sum(values), candidate.position, candidate.pmid)


def _features(candidate: SelectionCandidate) -> dict[str, object]:
    def signal(value: object | None, status: str = "available") -> dict[str, object]:
        return {"status": status if value is not None else "not_collected", "value": value}

    return {
        "pubmed_position": {"status": "available", "value": candidate.position},
        "publication_types": {"status": "available" if candidate.publication_types else "unavailable", "value": list(candidate.publication_types)},
        "abstract": {"status": "available" if candidate.has_abstract else "unavailable", "value": candidate.has_abstract},
        "mesh_match_count": {"status": "available", "value": candidate.mesh_match_count},
        "article_metrics": signal(candidate.article_score),
        "recent_citations": signal(candidate.recent_citations),
        "cited_by_count": signal(candidate.cited_by_count),
        "journal_metrics": signal(candidate.journal_metric),
        "year": signal(candidate.year, "available"),
    }


def select_reading_plan(
    candidates: list[SelectionCandidate], target_core_count: int = 12
) -> list[SelectedItem]:
    """Return all snapshot candidates with mutually exclusive persisted roles."""
    quotas = allocate_core_quotas(candidates, target_core_count)
    grouped: dict[Stage, list[SelectionCandidate]] = {stage: [] for stage in STAGES}
    for candidate in candidates:
        grouped[classify_stage(candidate)].append(candidate)
    selected: list[SelectedItem] = []
    for stage in STAGES:
        ranked = sorted(grouped[stage], key=_score_key)
        for index, candidate in enumerate(ranked):
            role: Role = "core" if index < quotas[stage] else "candidate"
            features = _features(candidate)
            available = [name for name, signal in features.items() if signal["status"] == "available"]  # type: ignore[index]
            selected.append(
                SelectedItem(
                    pmid=candidate.pmid,
                    stage=stage,
                    role=role,
                    stage_order=index,
                    recommendation_reason=(
                        f"Assigned to {stage} from PublicationType/recency; ranked using "
                        f"available metadata signals: {', '.join(available)}."
                    ),
                    evidence_features=features,
                    limitations=(
                        "Restricted full text not obtained was not analysed.",
                        "This is a metadata/abstract prioritisation, not a risk-of-bias assessment.",
                    ),
                )
            )
    return selected
