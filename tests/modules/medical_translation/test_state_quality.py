from dataclasses import replace

import pytest

from app.modules.medical_translation.cache_key import CacheIdentity, cache_key
from app.modules.medical_translation.quality import validate_translation
from app.modules.medical_translation.state_machine import (
    InvalidTranslationTransition,
    transition,
)


def test_state_machine_only_allows_frozen_phase_one_transitions():
    assert transition("queued", "running") == "running"
    assert transition("running", "quality_checking") == "quality_checking"
    assert transition("quality_checking", "succeeded") == "succeeded"
    assert transition("running", "failed") == "failed"
    assert transition("queued", "cancelled") == "cancelled"
    with pytest.raises(InvalidTranslationTransition):
        transition("succeeded", "running")
    with pytest.raises(InvalidTranslationTransition):
        transition("queued", "succeeded")


def test_cache_key_is_deterministic_and_version_sensitive():
    identity = CacheIdentity(
        access_scope="local",
        document_id=7,
        file_hash="a" * 64,
        anchor_revision_id=11,
        segmentation_revision_id=12,
        source_anchor_id=13,
        source_text_hash="b" * 64,
        source_language="en",
        target_language="zh-CN",
        context_hash="c" * 64,
        terminology_version="term-v1",
        provider="fake",
        model="deterministic",
        model_revision="r1",
        prompt_version="prompt-v1",
        config_version="config-v1",
        policy_version="policy-v1",
        validator_version="validator-v1",
    )
    assert cache_key(identity) == cache_key(identity)
    for field, changed in (
        ("source_text_hash", "d" * 64),
        ("model_revision", "r2"),
        ("prompt_version", "prompt-v2"),
        ("terminology_version", "term-v2"),
        ("validator_version", "validator-v2"),
    ):
        assert cache_key(identity) != cache_key(replace(identity, **{field: changed}))


@pytest.mark.parametrize(
    ("source", "target", "code"),
    [
        ("The response was 25%.", "应答率为 35%。", "NUMBER_MISMATCH"),
        ("P < 0.05.", "P > 0.05。", "COMPARATOR_MISMATCH"),
        ("95% CI 1.2-1.8.", "95% CI 1.2-2.8。", "INTERVAL_MISMATCH"),
        ("HR 0.72.", "RR 0.72。", "EFFECT_MEASURE_MISMATCH"),
        ("Take 5 mg twice daily.", "每日两次服用 50 mg。", "DOSE_MISMATCH"),
        ("Treatment was not effective.", "治疗有效。", "NEGATION_MISSING"),
        ("Treatment was higher than control.", "治疗低于对照。", "DIRECTION_MISMATCH"),
    ],
)
def test_deterministic_medical_checks_block_dangerous_changes(source, target, code):
    report = validate_translation(source, target)
    issue = next(item for item in report.issues if item.code == code)
    assert issue.severity in {"error", "critical"}
    assert issue.blocking is True
    assert issue.source_span is not None


def test_safe_translation_preserves_protected_medical_facts():
    report = validate_translation(
        "Treatment response was 25% (95% CI 20%-30%; P < 0.05), HR 0.72. "
        "Take 5 mg twice daily; treatment was not lower than control.",
        "治疗应答率为 25%（95% CI 20%-30%；P < 0.05），HR 0.72。"
        "每日两次服用 5 mg；治疗并不低于对照。",
    )
    assert report.blocked is False
    assert not [issue for issue in report.issues if issue.blocking]


def test_unresolved_abbreviation_is_explicit_and_not_fake_authority():
    report = validate_translation("XYZ improved response.", "XYZ 改善了应答。")
    term = next(item for item in report.terms if item.source_term == "XYZ")
    assert term.status == "unresolved"
    assert term.provenance == "phase1-local-rule"
    assert term.authority is None


@pytest.mark.parametrize(
    "target",
    [
        "医学" * 120,
        "这是译文。" + "史" * 80,
        "间质性肺病的筛查建议。" * 20,
    ],
)
def test_degenerate_repetition_is_blocked(target):
    report = validate_translation("Medical translation source text.", target)
    assert report.blocked is True
    assert any(issue.code == "DEGENERATE_REPETITION" for issue in report.issues)


def test_normal_medical_chinese_is_not_misclassified_as_degenerate():
    report = validate_translation(
        "Interstitial lung disease requires screening, diagnosis and monitoring.",
        "间质性肺病需要进行筛查、诊断和监测。",
    )
    assert not any(issue.code == "DEGENERATE_REPETITION" for issue in report.issues)


def test_unicode_replacement_artifacts_are_blocked():
    report = validate_translation("Medical evidence.", "医学证据���")
    assert report.blocked is True
    assert any(issue.code == "INVALID_UNICODE_OUTPUT" for issue in report.issues)
