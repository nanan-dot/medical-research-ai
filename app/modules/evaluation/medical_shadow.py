"""专家医学 Shadow 的本地、可复现评测契约；不生成医学标签。"""

from __future__ import annotations

import math
import random
import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.rag.shadow_release import ReleaseDecision


class PrivacyViolationError(ValueError):
    """正式标注含潜在 PHI；消息刻意不回显敏感内容。"""


LabelSource = Literal["synthetic_demo", "expert_annotation"]
EvidenceRole = Literal["direct", "indirect", "excluded"]
MetricStatus = Literal["available", "unavailable"]
_PHI_PATTERNS = (re.compile(r"\b1[3-9]\d{9}\b"), re.compile(r"\b\d{17}[\dXx]\b"), re.compile(r"(?:住院号|病历号)\s*[:：]?\s*\w+"))


class CandidateAnnotation(BaseModel):
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    source_identifier: str = Field(min_length=1)
    relevance: int = Field(ge=0, le=3)
    evidence_role: EvidenceRole
    numeric_value: str | None = None
    numeric_unit: str | None = None
    negated: bool = False
    citation_supported: bool | None = None
    numeric_verified: bool | None = None


class AnnotatorRecord(BaseModel):
    anonymous_id: str = Field(min_length=3)
    status: Literal["pending", "complete"]


class MedicalShadowCase(BaseModel):
    case_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    label_source: LabelSource
    frozen: bool = False
    question_type: str = Field(min_length=1)
    pico: dict[str, str] = Field(default_factory=dict)
    candidates: list[CandidateAnnotation] = Field(min_length=1)
    annotators: list[AnnotatorRecord] = Field(min_length=1)
    adjudication_status: Literal["pending", "complete"]
    notes: str = ""

    @model_validator(mode="after")
    def block_phi_in_formal_data(self) -> MedicalShadowCase:
        if self.label_source == "expert_annotation":
            strings: Iterable[str] = [self.notes, *self.pico.values()]
            if any(pattern.search(value) for value in strings for pattern in _PHI_PATTERNS):
                raise PrivacyViolationError(f"case_id={self.case_id}: potential PHI in annotation field")
        return self


def validate_formal_case(raw: object) -> MedicalShadowCase:
    """Ingestion boundary that does not expose Pydantic's raw invalid input."""
    try:
        return MedicalShadowCase.model_validate(raw)
    except ValidationError as error:
        case_id = raw.get("case_id", "<unknown>") if isinstance(raw, dict) else "<unknown>"
        if "potential PHI" in str(error):
            raise PrivacyViolationError(f"case_id={case_id}: potential PHI in annotation field") from None
        raise


class MetricValue(BaseModel):
    status: MetricStatus
    value: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    reason: str | None = None


class StrategyMetrics(BaseModel):
    ndcg_at_10: float
    ndcg_at_20: float
    mrr: float
    recall_at_50: float
    precision_at_10: float
    exclusion_precision: float | None = None


class CaseShadowResult(BaseModel):
    case_id: str
    baseline: StrategyMetrics
    candidate: StrategyMetrics


class MedicalShadowReport(BaseModel):
    dataset_version: str
    seed: int
    cases: list[CaseShadowResult]
    aggregate: dict[str, MetricValue]
    exploratory: bool
    fairness_contract: str = "same_frozen_candidate_ids"


def _metrics(case: MedicalShadowCase, order: list[str]) -> StrategyMetrics:
    by_chunk = {candidate.chunk_id: candidate for candidate in case.candidates}
    labels = [by_chunk.get(chunk_id, CandidateAnnotation(document_id="unknown", chunk_id=chunk_id, source_identifier="unknown", relevance=0, evidence_role="excluded")).relevance for chunk_id in order]
    def ndcg(k: int) -> float:
        actual = sum(((2**label - 1) / math.log2(index + 2)) for index, label in enumerate(labels[:k]))
        ideal_labels = sorted((item.relevance for item in case.candidates), reverse=True)
        ideal = sum(((2**label - 1) / math.log2(index + 2)) for index, label in enumerate(ideal_labels[:k]))
        return actual / ideal if ideal else 0.0
    relevant = [label > 0 for label in labels]
    first = next((index + 1 for index, value in enumerate(relevant) if value), None)
    all_relevant = {item.chunk_id for item in case.candidates if item.relevance > 0}
    top = labels[:10]
    excluded_predictions = [chunk for chunk in order if chunk in by_chunk and by_chunk[chunk].evidence_role == "excluded"]
    excluded_correct = [chunk for chunk in excluded_predictions if by_chunk[chunk].relevance == 0]
    return StrategyMetrics(ndcg_at_10=ndcg(10), ndcg_at_20=ndcg(20), mrr=0.0 if first is None else 1 / first, recall_at_50=len(all_relevant.intersection(order[:50])) / len(all_relevant) if all_relevant else 1.0, precision_at_10=sum(label > 0 for label in top) / len(top) if top else 0.0, exclusion_precision=len(excluded_correct) / len(excluded_predictions) if excluded_predictions else None)


class MedicalShadowRunner:
    def __init__(self, *, seed: int, bootstrap_samples: int = 1000) -> None:
        self.seed, self.bootstrap_samples = seed, bootstrap_samples

    def run(self, cases: list[MedicalShadowCase], *, baseline_orders: dict[str, list[str]], candidate_orders: dict[str, list[str]]) -> MedicalShadowReport:
        results = [CaseShadowResult(case_id=case.case_id, baseline=_metrics(case, baseline_orders[case.case_id]), candidate=_metrics(case, candidate_orders[case.case_id])) for case in cases]
        aggregate = self._aggregate(cases, results)
        return MedicalShadowReport(dataset_version=cases[0].dataset_version, seed=self.seed, cases=results, aggregate=aggregate, exploratory=any(case.label_source != "expert_annotation" or not case.frozen or case.adjudication_status != "complete" for case in cases))

    def _aggregate(self, cases: list[MedicalShadowCase], results: list[CaseShadowResult]) -> dict[str, MetricValue]:
        fields = ("ndcg_at_10", "ndcg_at_20", "mrr", "recall_at_50", "precision_at_10", "exclusion_precision")
        answer_fields = {"citation_support_rate": [item.citation_supported for case in cases for item in case.candidates], "numeric_verified_rate": [item.numeric_verified for case in cases for item in case.candidates], "no_answer_rate": []}
        output: dict[str, MetricValue] = {}
        for field in fields:
            values = [getattr(item.candidate, field) for item in results if getattr(item.candidate, field) is not None]
            output[field] = self._bootstrap(values)
        for name, values in answer_fields.items():
            known = [float(value) for value in values if value is not None]
            output[name] = self._bootstrap(known) if known else MetricValue(status="unavailable", reason="label_not_present")
        return output

    def _bootstrap(self, values: list[float]) -> MetricValue:
        if not values:
            return MetricValue(status="unavailable", reason="label_not_present")
        randomizer = random.Random(self.seed)
        samples = sorted(sum(randomizer.choice(values) for _ in values) / len(values) for _ in range(self.bootstrap_samples))
        return MetricValue(status="available", value=sum(values) / len(values), ci_low=samples[int(.025 * (len(samples) - 1))], ci_high=samples[int(.975 * (len(samples) - 1))])


class PerformanceBudget(BaseModel):
    approved: bool = False
    source: str | None = None
    cold_start_ms: int | None = Field(default=None, gt=0)
    warm_p95_ms: int | None = Field(default=None, gt=0)
    top_k: int | None = Field(default=None, gt=0)
    batch_size: int | None = Field(default=None, gt=0)
    concurrency: int | None = Field(default=None, gt=0)
    p99_ms: int | None = Field(default=None, gt=0)
    max_failure_rate: float | None = Field(default=None, ge=0, le=1)


class ShadowReleaseEvidence(BaseModel):
    frozen_expert_dataset: bool = False
    adjudication_complete: bool = False
    effect_gate_passed: bool = False
    safety_citation_gate_passed: bool = False
    performance_budget: PerformanceBudget = Field(default_factory=PerformanceBudget)
    frozen_shadow_report_id: str | None = None
    report_frozen: bool = False


def evaluate_medical_shadow_release_gate(evidence: ShadowReleaseEvidence) -> ReleaseDecision:
    checks = {"frozen_expert_dataset": evidence.frozen_expert_dataset, "adjudication_complete": evidence.adjudication_complete, "effect_gate": evidence.effect_gate_passed, "safety_citation_gate": evidence.safety_citation_gate_passed, "approved_performance_budget": evidence.performance_budget.approved, "frozen_shadow_report": bool(evidence.frozen_shadow_report_id) and evidence.report_frozen}
    missing = [name for name, passed in checks.items() if not passed]
    return ReleaseDecision(release_eligible=not missing, missing_hard_gates=missing)
