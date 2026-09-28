from app.rag.medical_normalizer import NORMALIZER_VERSION, normalize_medical_text


def test_wp1_01_her2_positive_and_negative_remain_distinct() -> None:
    assert normalize_medical_text("HER2+").tokens != normalize_medical_text("HER2-").tokens


def test_wp1_02_pd_l1_threshold_preserves_metric_comparator_value_and_unit() -> None:
    result = normalize_medical_text("PD-L1 TPS ≥50%")
    assert {"pd-l1", "tps", "≥", "50", "%"}.issubset(result.tokens)


def test_wp1_03_variant_relationships_are_not_split_apart() -> None:
    tokens = normalize_medical_text("KRAS G12C EGFR T790M c.35G>T").tokens
    assert {"kras_g12c", "egfr_t790m", "c.35g>t"}.issubset(tokens)


def test_wp1_04_chinese_bigrams_are_preserved() -> None:
    assert "奥希" in normalize_medical_text("奥希替尼").tokens


def test_wp1_05_raw_text_is_not_overwritten() -> None:
    raw = "PD-L1 TPS ≥50%"
    assert normalize_medical_text(raw).raw_text == raw


def test_wp1_06_normalization_is_deterministic_and_versioned() -> None:
    assert normalize_medical_text("HER2+") == normalize_medical_text("HER2+")
    assert normalize_medical_text("HER2+").version == NORMALIZER_VERSION
