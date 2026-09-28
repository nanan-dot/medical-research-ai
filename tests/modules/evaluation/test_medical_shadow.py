from app.modules.evaluation.medical_shadow import (
    MedicalShadowCase,
    MedicalShadowRunner,
    PerformanceBudget,
    PrivacyViolationError,
    ShadowReleaseEvidence,
    evaluate_medical_shadow_release_gate,
    validate_formal_case,
)


def case() -> MedicalShadowCase:
    return MedicalShadowCase.model_validate({
        "case_id": "demo-001",
        "dataset_version": "demo-v1",
        "label_source": "synthetic_demo",
        "frozen": False,
        "question_type": "therapy",
        "pico": {"population": "synthetic", "intervention": "sotorasib"},
        "candidates": [
            {"document_id": "d1", "chunk_id": "c1", "source_identifier": "demo:1", "relevance": 3, "evidence_role": "direct", "citation_supported": True, "numeric_verified": True},
            {"document_id": "d2", "chunk_id": "c2", "source_identifier": "demo:2", "relevance": 0, "evidence_role": "excluded", "citation_supported": False, "numeric_verified": False},
        ],
        "annotators": [{"anonymous_id": "expert-a", "status": "complete"}],
        "adjudication_status": "pending",
    })


def test_shadow_runner_compares_same_frozen_candidates_and_marks_missing_labels_unavailable() -> None:
    report = MedicalShadowRunner(seed=7, bootstrap_samples=100).run(
        [case()], baseline_orders={"demo-001": ["c2", "c1"]}, candidate_orders={"demo-001": ["c1", "c2"]}
    )
    assert report.cases[0].baseline.ndcg_at_10 < report.cases[0].candidate.ndcg_at_10
    assert report.aggregate["citation_support_rate"].status == "available"
    assert report.aggregate["no_answer_rate"].status == "unavailable"
    assert report.exploratory is True


def test_formal_case_rejects_phi_without_exposing_original_text() -> None:
    raw = case().model_dump()
    raw["label_source"] = "expert_annotation"
    raw["frozen"] = True
    raw["notes"] = "Call 13800138000"
    try:
        validate_formal_case(raw)
    except PrivacyViolationError as error:
        assert "demo-001" in str(error)
        assert "13800138000" not in str(error)
    else:
        raise AssertionError("PHI must block a formal case")


def test_release_gate_requires_frozen_expert_dataset_adjudication_metrics_budget_and_report() -> None:
    decision = evaluate_medical_shadow_release_gate(ShadowReleaseEvidence())
    assert decision.release_eligible is False
    assert "frozen_expert_dataset" in decision.missing_hard_gates
    assert evaluate_medical_shadow_release_gate(
        ShadowReleaseEvidence(
            frozen_expert_dataset=True, adjudication_complete=True, effect_gate_passed=True,
            safety_citation_gate_passed=True, performance_budget=PerformanceBudget(approved=True),
            frozen_shadow_report_id="r1", report_frozen=True,
        )
    ).release_eligible is True
