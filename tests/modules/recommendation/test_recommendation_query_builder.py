import pytest

from app.modules.recommendation.query_builder import RecommendationQueryBuilder


def test_builds_pubmed_query_from_curated_chinese_terms() -> None:
    result = RecommendationQueryBuilder().build("肺癌免疫治疗综述")

    assert "Lung Neoplasms" in result.boolean_query
    assert "Immunotherapy" in result.boolean_query
    assert '"Review"[Publication Type]' in result.boolean_query
    assert result.term_sources["disease"] == "curated_local_mapping"


def test_rejects_empty_and_overlong_requests() -> None:
    builder = RecommendationQueryBuilder()

    with pytest.raises(ValueError, match="non-empty"):
        builder.build(" ")
    with pytest.raises(ValueError, match="1000"):
        builder.build("a" * 1001)


def test_does_not_invent_translation_for_unknown_chinese_terms() -> None:
    with pytest.raises(ValueError, match="safe"):
        RecommendationQueryBuilder().build("罕见未收录疾病")


def test_rejects_query_control_characters() -> None:
    with pytest.raises(ValueError, match="unsafe"):
        RecommendationQueryBuilder().build("lung cancer; DROP")
