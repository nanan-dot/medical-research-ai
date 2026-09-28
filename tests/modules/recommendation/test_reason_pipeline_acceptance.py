"""AC-RR-03--09 acceptance tests for the deterministic reason boundary."""

import json

from app.modules.recommendation.reason_pipeline import (
    OUTPUT_SCHEMA_VERSION,
    compile_fact_packet,
    narration_prompt,
    validate_polished_reason,
)


def _packet(*, overlap: str = "novel", abstract_missing: bool = False):
    limits = [{"code": "abstract_unavailable", "message": "未提供摘要，需结合全文核验。"}] if abstract_missing else []
    return compile_fact_packet(
        source_result_id=7, intent_snapshot_id=2, exploration_query=None,
        recommendation_mode="balanced", year=2024,
        publication_types=["Randomized Controlled Trial"], overlap_status=overlap,
        matches=[{"dimension": "disease", "status": "matched", "matched_terms": ["肺癌"], "field": "title", "excerpt": "PRIVATE_ARTICLE_SOURCE_TEXT"}], limitations=limits,
    )


def _output(packet, **replacement):
    limitation_id = packet.limitations[0].fact_id
    values = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "headline": {"text": "肺癌相关候选", "fact_ids": [packet.topic_matches[0].fact_id]},
        "relevance": {"text": "肺癌与当前主题匹配", "fact_ids": [packet.topic_matches[0].fact_id]},
        "incremental_value": {"text": packet.incremental_value.display_text, "fact_ids": [packet.incremental_value.fact_id]},
        "limitation": {"text": packet.limitations[0].message, "fact_ids": [limitation_id]},
    }
    values.update(replacement)
    return json.dumps(values, ensure_ascii=False)


def test_ac_rr_03_fact_packet_is_versioned_and_all_visible_facts_are_traceable() -> None:
    packet = _packet()
    assert packet.schema_version == "recommendation-reason-facts-v1"
    assert len({fact.fact_id for fact in packet.topic_matches}) == len(packet.topic_matches)
    assert packet.topic_matches[0].source_field == "title"
    assert packet.topic_matches[0].verification_status == "verified"


def test_ac_rr_04_base_reason_handles_covered_and_missing_abstract_without_new_claims() -> None:
    packet = _packet(overlap="covered", abstract_missing=True)
    assert "已在当前集合" in packet.base_reason.incremental_value
    assert "未提供摘要" in packet.base_reason.limitation
    assert "疗效" not in packet.base_reason.model_dump_json()


def test_ac_rr_05_model_prompt_excludes_identity_and_source_text() -> None:
    prompt = narration_prompt(_packet())
    payload = prompt.split("\n", maxsplit=1)[1]
    assert all(value not in payload for value in ("source_result_id", "PMID", "DOI", "作者", "期刊", "PRIVATE_ARTICLE_SOURCE_TEXT"))
    assert "只能依据事实包" in prompt


def test_ac_rr_06_unknown_fact_id_rejects_entire_response() -> None:
    packet = _packet()
    raw = _output(packet, relevance={"text": "肺癌与当前主题匹配", "fact_ids": ["topic:invented"]})
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code == "narration_unknown_fact_id"


def test_ac_rr_07_new_number_or_entity_rejects_entire_response() -> None:
    packet = _packet()
    raw = _output(packet, relevance={"text": "阿司匹林可改善99例肺癌患者", "fact_ids": [packet.topic_matches[0].fact_id]})
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code in {"narration_new_number", "narration_new_entity"}


def test_ac_rr_08_medical_overclaim_rejects_entire_response() -> None:
    packet = _packet()
    raw = _output(packet, relevance={"text": "肺癌治疗显著改善疗效", "fact_ids": [packet.topic_matches[0].fact_id]})
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code == "narration_medical_boundary"


def test_ac_rr_09_required_limitation_must_be_bound_in_limitation_section() -> None:
    packet = _packet(abstract_missing=True)
    raw = _output(packet, limitation={"text": "请结合全文核验。", "fact_ids": [packet.topic_matches[0].fact_id]})
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code == "narration_required_disclosure_missing"


def test_prism_rejects_chinese_entity_and_relation_not_in_packet() -> None:
    packet = _packet()
    raw = _output(
        packet,
        relevance={
            "text": "肺癌与痴呆有关",
            "fact_ids": [packet.topic_matches[0].fact_id],
        },
    )
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code == "narration_new_entity"


def test_prism_requires_required_limitation_text_not_only_its_fact_id() -> None:
    packet = _packet(abstract_missing=True)
    raw = _output(
        packet,
        limitation={
            "text": "需要进一步核验。",
            "fact_ids": [packet.limitations[0].fact_id],
        },
    )
    output, validation = validate_polished_reason(packet, raw)
    assert output is None
    assert validation.error_code == "narration_required_disclosure_missing"


def test_prism_compiler_assigns_distinct_ids_to_duplicate_match_rows() -> None:
    packet = compile_fact_packet(
        source_result_id=7,
        intent_snapshot_id=2,
        exploration_query=None,
        recommendation_mode="balanced",
        year=None,
        publication_types=[],
        overlap_status="novel",
        matches=[
            {"dimension": "disease", "status": "matched", "matched_terms": ["肺癌"], "field": "title"},
            {"dimension": "disease", "status": "matched", "matched_terms": ["肺癌"], "field": "abstract"},
        ],
        limitations=[],
    )
    assert len({fact.fact_id for fact in packet.topic_matches}) == 2


def test_prism_mixed_candidate_outcomes_are_visible_at_run_level() -> None:
    from app.modules.recommendation.v5_service import RecommendationV5Service

    assert (
        RecommendationV5Service._narration_summary(["completed", "fallback_timeout"])
        == "completed_with_fallback"
    )
    assert (
        RecommendationV5Service._narration_summary(
            ["fallback_timeout", "fallback_rejected"]
        )
        == "completed_with_fallback"
    )
