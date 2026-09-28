"""用户截图所暴露的推荐质量回归。"""

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.article_context import study_design_matches
from app.modules.recommendation.exploration import build_exploration_plan
from app.modules.recommendation.reason_pipeline import compile_fact_packet


def test_original_question_reuses_executed_query_and_requires_both_core_concepts():
    question = "间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？"
    query = '("interstitial lung disease"[Title/Abstract] OR "ILD"[Title/Abstract]) AND (nintedanib OR pirfenidone)'
    plan = build_exploration_plan(question, original_question=question, executed_query=query)
    assert plan.query == query
    assert not plan.evaluate(CitationItem(pmid="unrelated", title="Within-person reliability of composite scores"))[0]
    assert not plan.evaluate(CitationItem(pmid="partial", title="Interstitial lung disease induced by monoclonal antibodies"))[0]
    assert not plan.evaluate(CitationItem(pmid="substring", title="Children treated with nintedanib"))[0]
    eligible, matches = plan.evaluate(CitationItem(pmid="good", title="Nintedanib in interstitial lung disease"))
    assert eligible
    assert any("nintedanib" in match["matched_terms"] for match in matches)


def test_edited_query_retains_boolean_scope_and_exclusions():
    plan = build_exploration_plan('(fibrosis OR ILD) AND nintedanib NOT animals')
    assert plan.evaluate(CitationItem(pmid="a", title="ILD nintedanib"))[0]
    assert not plan.evaluate(CitationItem(pmid="b", title="fibrosis only"))[0]
    assert not plan.evaluate(CitationItem(pmid="c", title="ILD nintedanib animals"))[0]


def test_unmapped_chinese_query_fails_closed():
    import pytest

    with pytest.raises(ValueError, match="英文检索式"):
        build_exploration_plan("一个没有经过解析的中文医学问题")


def test_chinese_edit_must_not_silently_drop_unmapped_constraints():
    import pytest

    with pytest.raises(ValueError, match="英文检索式"):
        build_exploration_plan("间质性肺疾病患者中某个未映射的新药及特定亚组")


def test_query_field_scope_and_dates_are_not_treated_as_topic_evidence():
    plan = build_exploration_plan('fibrosis[Title] AND ("2020"[Date - Publication] : "2026"[Date - Publication])')
    assert plan.evaluate(CitationItem(pmid="yes", title="Fibrosis cohort", year=2024))[0]
    assert not plan.evaluate(CitationItem(pmid="abstract-only", title="Cohort", abstract="Fibrosis", year=2024))[0]
    assert not plan.evaluate(CitationItem(pmid="old", title="Fibrosis", year=2010))[0]


def test_each_reason_names_its_matched_terms_and_does_not_assert_missing_relevance():
    def compile(matches):
        return compile_fact_packet(source_result_id=1, intent_snapshot_id=None,
            exploration_query="ILD AND (nintedanib OR pirfenidone)",
            recommendation_mode="balanced", year=2024, publication_types=["Journal Article"],
            overlap_status="novel", matches=matches, limitations=[])
    first = compile([{"dimension":"topic", "status":"matched", "matched_terms":["nintedanib"], "field":"pubmed_title"}])
    second = compile([{"dimension":"topic", "status":"matched", "matched_terms":["pirfenidone"], "field":"pubmed_abstract_results"}])
    assert first.base_reason.headline != second.base_reason.headline
    assert "nintedanib" in first.base_reason.relevance
    assert "摘要" in second.base_reason.relevance
    missing = compile([])
    assert "相关" not in missing.base_reason.headline
    assert "有限关联" not in missing.base_reason.relevance


def test_study_design_is_extracted_from_title_or_publication_type_only():
    title_matches = study_design_matches(
        CitationItem(pmid="design-title", title="A single-arm phase 2 study of nintedanib")
    )
    assert title_matches[0]["display_text"] == "题名提供单臂研究线索"
    assert title_matches[0]["excerpt"] == "A single-arm phase 2 study of nintedanib"

    type_matches = study_design_matches(
        CitationItem(
            pmid="design-type",
            title="Nintedanib for pulmonary fibrosis",
            publication_types=["Randomized Controlled Trial"],
        )
    )
    assert type_matches[0]["display_text"] == "文献类型提供随机对照试验线索"


def test_abstract_mentions_and_non_randomized_titles_do_not_create_false_rct_claims():
    abstract_only = CitationItem(
        pmid="abstract-only",
        title="Nintedanib in clinical practice",
        abstract="We compare our cohort with a randomized controlled trial.",
        publication_types=["Journal Article"],
    )
    assert study_design_matches(abstract_only) == []

    non_randomized = CitationItem(
        pmid="not-rct",
        title="A non-randomized controlled trial of nintedanib",
    )
    assert all(
        match["matched_terms"] != ["randomized controlled trial"]
        for match in study_design_matches(non_randomized)
    )
