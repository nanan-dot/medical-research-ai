"""WP0's reproducible, annotation-only literature-ranking baseline.

This module evaluates an already-produced order.  It deliberately does not
alter literature-search ordering or infer medical labels from article metadata.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

RelevanceLabel = Literal[-1, 0, 1, 2, 3]
EligibilityLabel = Literal["eligible", "possibly_eligible", "excluded", "unknown"]
LabelSource = Literal["synthetic_fixture", "expert_annotation"]

LEGACY_CLASSIC_BASELINE_STATUS = "legacy_proxy"
NO_EXPERT_GOLD_STANDARD_STATUS = "not_validated_without_expert_gold_standard"


class LiteratureRankingCase(BaseModel):
    """One immutable annotation case for ranking evaluation.

    ``synthetic_fixture`` supports contract tests only and must never be
    presented as an expert medical gold standard.
    """

    case_id: str = Field(min_length=1, max_length=100)
    result_fixture_id: str = Field(min_length=1, max_length=100)
    research_intent: dict[str, object] = Field(min_length=1)
    relevance_labels_by_pmid: dict[str, RelevanceLabel] = Field(min_length=1)
    eligibility_labels_by_pmid: dict[str, EligibilityLabel] = Field(default_factory=dict)
    dimension_labels_by_pmid: dict[str, dict[str, RelevanceLabel]] = Field(
        default_factory=dict
    )
    required_pmids: list[str] = Field(default_factory=list)
    forbidden_pmids: list[str] = Field(default_factory=list)
    notes: str = ""
    label_source: LabelSource

    @field_validator("relevance_labels_by_pmid", "eligibility_labels_by_pmid")
    @classmethod
    def validate_pmid_keys_are_present(cls, labels: dict[str, object]) -> dict[str, object]:
        if any(not pmid.strip() for pmid in labels):
            raise ValueError("PMID label keys must be non-empty")
        return labels


@dataclass(frozen=True)
class LiteratureRankingMetrics:
    """Metrics for a fixed result order and optional eligibility prediction."""

    ndcg_at_10: float
    ndcg_at_20: float
    mrr: float
    recall_at_50: float
    precision_at_10: float
    exclusion_precision: float | None


@dataclass(frozen=True)
class LiteratureRankingBaselineReport(LiteratureRankingMetrics):
    """WP0 result metadata makes legacy and validation limits explicit."""

    case_id: str
    algorithm_version: str
    classic_baseline_status: str
    medical_effect_status: str


def _gain(label: int) -> float:
    return float((2**label) - 1) if label > 0 else 0.0


def _ndcg_at_k(labels: list[int], k: int) -> float:
    observed = sum(_gain(label) / math.log2(index + 2) for index, label in enumerate(labels[:k]))
    ideal = sorted(labels, reverse=True)
    ideal_dcg = sum(_gain(label) / math.log2(index + 2) for index, label in enumerate(ideal[:k]))
    return observed / ideal_dcg if ideal_dcg else 0.0


def _mrr(labels: list[int]) -> float:
    first_relevant_rank = next((index + 1 for index, label in enumerate(labels) if label > 0), None)
    return 0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank


def _precision_at_10(labels: list[int]) -> float:
    top_k = labels[:10]
    return sum(label > 0 for label in top_k) / len(top_k) if top_k else 0.0


def _recall_at_50(case: LiteratureRankingCase, ranked_pmids: list[str]) -> float:
    required = set(case.required_pmids)
    if not required:
        return 1.0
    return len(required.intersection(ranked_pmids[:50])) / len(required)


def _exclusion_precision(
    case: LiteratureRankingCase, predicted_excluded_pmids: list[str] | None
) -> float | None:
    if predicted_excluded_pmids is None:
        return None
    if not predicted_excluded_pmids:
        return 1.0
    forbidden = set(case.forbidden_pmids)
    return len(forbidden.intersection(predicted_excluded_pmids)) / len(predicted_excluded_pmids)


def evaluate_ranking(
    case: LiteratureRankingCase,
    ranked_pmids: list[str],
    *,
    predicted_excluded_pmids: list[str] | None = None,
) -> LiteratureRankingBaselineReport:
    """Evaluate a fixed order without changing it or deriving new labels."""
    labels = [case.relevance_labels_by_pmid.get(pmid, 0) for pmid in ranked_pmids]
    medical_effect_status = (
        "expert_gold_standard_available"
        if case.label_source == "expert_annotation"
        else NO_EXPERT_GOLD_STANDARD_STATUS
    )
    return LiteratureRankingBaselineReport(
        case_id=case.case_id,
        algorithm_version="literature-ranking-baseline-v1",
        ndcg_at_10=_ndcg_at_k(labels, 10),
        ndcg_at_20=_ndcg_at_k(labels, 20),
        mrr=_mrr(labels),
        recall_at_50=_recall_at_50(case, ranked_pmids),
        precision_at_10=_precision_at_10(labels),
        exclusion_precision=_exclusion_precision(case, predicted_excluded_pmids),
        classic_baseline_status=LEGACY_CLASSIC_BASELINE_STATUS,
        medical_effect_status=medical_effect_status,
    )


def load_literature_ranking_jsonl(path: Path) -> list[LiteratureRankingCase]:
    """Load cases while reporting the source ``case_id`` and invalid field."""
    if not path.is_file():
        raise FileNotFoundError(f"Literature ranking dataset does not exist: {path}")
    cases: list[LiteratureRankingCase] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            raw_case = json.loads(raw_line)
            case_id = raw_case.get("case_id", "<unknown>") if isinstance(raw_case, dict) else "<unknown>"
            cases.append(LiteratureRankingCase.model_validate(raw_case))
        except json.JSONDecodeError as error:
            raise ValueError(f"Literature ranking dataset line {line_number} is invalid JSON") from error
        except ValidationError as error:
            field = ".".join(str(part) for part in error.errors()[0]["loc"])
            raise ValueError(
                f"Literature ranking dataset validation failed for case_id='{case_id}' at field '{field}'"
            ) from error
    if not cases:
        raise ValueError("Literature ranking dataset is empty")
    return cases
