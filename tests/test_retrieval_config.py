import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_wp2_legacy_search_top_k_maps_all_retrieval_stages() -> None:
    settings = Settings(SEARCH_TOP_K=7)
    assert (settings.DENSE_TOP_K, settings.SPARSE_TOP_K, settings.FUSION_TOP_K) == (7, 7, 7)


def test_wp2_explicit_new_field_wins_over_legacy_value() -> None:
    settings = Settings(SEARCH_TOP_K=7, DENSE_TOP_K=11)
    assert settings.DENSE_TOP_K == 11
    assert settings.retrieval_config_notice == "SEARCH_TOP_K ignored where explicit stage values exist"


def test_wp2_default_profile_is_local_evidence() -> None:
    settings = Settings()
    assert (settings.RETRIEVAL_PROFILE, settings.DENSE_TOP_K, settings.SPARSE_TOP_K, settings.FUSION_TOP_K, settings.RERANK_TOP_K, settings.LLM_CONTEXT_TOP_K) == ("local_evidence", 30, 30, 40, 8, 6)


def test_wp2_rejects_invalid_stage_relationship() -> None:
    with pytest.raises(ValidationError):
        Settings(FUSION_TOP_K=4, RERANK_TOP_K=5)


def test_wp2_rejects_unknown_profile() -> None:
    with pytest.raises(ValidationError):
        Settings(RETRIEVAL_PROFILE="unknown")


def test_navigation_rerank_initialization_and_inference_timeouts_are_independent() -> None:
    settings = Settings(
        NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS=45,
        NAVIGATION_RERANK_TIMEOUT_SECONDS=12,
    )

    assert settings.NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS == 45
    assert settings.NAVIGATION_RERANK_TIMEOUT_SECONDS == 12
