import pytest

from app.rag.schemas import QueryPlan, RetrievalTrace
from app.rag.shadow_release import (
    ReleaseEvidence,
    ShadowComparisonRunner,
    ShadowExecutionError,
    StrategyOutcome,
    evaluate_release_gate,
    render_release_report,
    resolve_user_visible_mode,
)


class FakeStrategy:
    def __init__(self, outcome: StrategyOutcome | Exception) -> None:
        self._outcome = outcome

    def compare(self, trace: RetrievalTrace) -> StrategyOutcome:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def _trace() -> RetrievalTrace:
    return RetrievalTrace(trace_id="trace-9", query_plan=QueryPlan(query="not persisted"))


def test_wp9_comparison_uses_same_trace_and_marks_missing_assets_unavailable() -> None:
    report = ShadowComparisonRunner(
        {
            "bm25": FakeStrategy(StrategyOutcome(candidate_ids=["b1"])),
            "dense": FakeStrategy(StrategyOutcome(candidate_ids=["d1"])),
            "hybrid_rrf": FakeStrategy(StrategyOutcome(candidate_ids=["h1"])),
            "paperqa2": FakeStrategy(StrategyOutcome(answer_status="ready")),
        }
    ).compare(_trace())

    assert report.trace_id == "trace-9"
    assert report.by_strategy("hybrid_rrf_reranker").status == "unavailable"
    assert report.by_strategy("grounded").status == "unavailable"
    assert report.by_strategy("paperqa2").status == "completed"


def test_wp9_strategy_failure_is_isolated_and_report_contains_no_question_text() -> None:
    report = ShadowComparisonRunner(
        {"bm25": FakeStrategy(ShadowExecutionError("down"))}
    ).compare(_trace())
    rendered = render_release_report(report, evaluate_release_gate(ReleaseEvidence()))

    assert report.by_strategy("bm25").status == "failed"
    assert "not persisted" not in rendered
    assert "bm25: failed" in rendered


@pytest.mark.parametrize("mode", ["paperqa", "shadow", "grounded"])
def test_wp9_shadow_and_disabled_flag_preserve_paperqa_visible_mode(mode: str) -> None:
    assert resolve_user_visible_mode(mode, is_new_chain_enabled=False) == "paperqa"


def test_wp9_release_gate_refuses_default_release_when_hard_evidence_is_missing() -> None:
    decision = evaluate_release_gate(ReleaseEvidence(frozen_report_id="shadow-v1"))

    assert decision.release_eligible is False
    assert set(decision.missing_hard_gates) == {
        "actual_reranker_model",
        "grounded_generator",
        "medical_expert_gold_standard",
        "production_latency_budget",
        "frozen_comparison_report",
    }


def test_wp9_release_gate_requires_all_frozen_hard_gates() -> None:
    decision = evaluate_release_gate(
        ReleaseEvidence(
            frozen_report_id="shadow-v1",
            report_frozen=True,
            actual_reranker_available=True,
            grounded_generator_available=True,
            medical_gold_standard_available=True,
            production_latency_budget_frozen=True,
        )
    )

    assert decision.release_eligible is True and decision.missing_hard_gates == []
