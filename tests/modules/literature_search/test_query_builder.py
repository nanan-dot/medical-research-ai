import pytest

from app.modules.literature_search.mesh_client import MeshClient
from app.modules.literature_search.query_builder import build_boolean_query
from app.modules.literature_search.query_model import SearchIntentCandidate
from app.modules.literature_search.schema import SearchTermGroup
from app.modules.literature_search.service import LiteratureSearchService


async def test_expands_synonyms_and_official_mesh_candidates() -> None:
    async def fetcher(term: str):
        assert term == "Metformin"
        return [
            {"label": "Metformin", "resource": "http://id.nlm.nih.gov/mesh/D008687"}
        ]

    service = LiteratureSearchService(None, mesh_client=MeshClient(fetcher))  # type: ignore[arg-type]
    response = await service.expand_terms(
        SearchIntentCandidate(topic="metformin for diabetes", intervention="metformin"),
        {"intervention": ["MET"]},
    )

    assert response.term_groups[0].terms == ["metformin", "dimethylbiguanide", "MET"]
    assert response.mesh_candidates[0].mesh_id == "D008687"
    assert response.mesh_candidates[0].source == "NLM MeSH"


async def test_empty_mesh_is_valid_and_does_not_invent_descriptor() -> None:
    async def fetcher(_: str):
        return []

    service = LiteratureSearchService(None, mesh_client=MeshClient(fetcher))  # type: ignore[arg-type]
    response = await service.expand_terms(
        SearchIntentCandidate(topic="EGFR", target="EGFR"), {}
    )

    assert response.mesh_candidates == []
    assert response.term_groups[0].terms == [
        "epidermal growth factor receptor",
        "ERBB1",
    ]


async def test_expands_curated_chinese_rectal_cancer_and_neoadjuvant_immunotherapy() -> None:
    async def fetcher(_: str) -> list[dict[str, str]]:
        return []

    service = LiteratureSearchService(None, mesh_client=MeshClient(fetcher))  # type: ignore[arg-type]
    response = await service.expand_terms(
        SearchIntentCandidate(
            topic="局部晚期直肠癌患者加入新辅助免疫治疗",
            disease="局部晚期直肠癌",
            intervention="新辅助免疫治疗",
        ),
        {},
    )

    assert [group.name for group in response.term_groups] == ["disease", "intervention"]
    assert response.term_groups[0].terms == [
        "locally advanced rectal cancer",
        "locally advanced rectal neoplasm",
    ]
    assert response.term_groups[1].terms == [
        "neoadjuvant immunotherapy",
        "neoadjuvant immune checkpoint inhibitor",
    ]
    assert not any("Chinese-only" in warning for warning in response.warnings)


@pytest.mark.parametrize(
    "disease, intervention",
    [
        ("局部晚期直肠癌", "新辅助免疫治疗"),
        ("局部晚期直肠癌患者", "新辅助免疫治疗联合标准新辅助放化疗"),
        ("接受新辅助免疫治疗的局部晚期直肠癌", "接受新辅助免疫治疗"),
        ("局部晚期直肠癌（LARC）", "新辅助免疫治疗（PD-1 抑制剂）"),
        ("局部 晚期 直肠癌", "新辅助 免疫治疗"),
    ],
)
async def test_normalizes_five_common_chinese_clinical_phrase_formats(
    disease: str,
    intervention: str,
) -> None:
    async def fetcher(_: str) -> list[dict[str, str]]:
        return []

    service = LiteratureSearchService(None, mesh_client=MeshClient(fetcher))  # type: ignore[arg-type]
    response = await service.expand_terms(
        SearchIntentCandidate(topic=f"{disease} {intervention}", disease=disease, intervention=intervention),
        {},
    )

    term_groups = {group.name: group.terms for group in response.term_groups}
    assert "locally advanced rectal cancer" in term_groups["disease"]
    assert "neoadjuvant immunotherapy" in term_groups["intervention"]
    assert not any("Chinese-only" in warning for warning in response.warnings)


def test_unknown_chinese_term_remains_unmapped_instead_of_inventing_translation() -> None:
    from app.modules.literature_search.term_expansion import expand_term

    expansion = expand_term("未收录的治疗概念")

    assert expansion.source == "user_supplied"
    assert expansion.synonyms == ("未收录的治疗概念",)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("gastric cancer", "Gastric Neoplasms"),
        ("lung cancer", "Lung Neoplasms"),
        ("breast cancer", "Breast Neoplasms"),
        ("diabetes", "Diabetes Mellitus"),
        ("alzheimer disease", "Alzheimer Disease"),
        ("immunotherapy", "Immunotherapy"),
        ("metformin", "Metformin"),
        ("aspirin", "Aspirin"),
        ("egfr", "EGFR"),
        ("brca1", "BRCA1"),
    ],
)
def test_curated_real_topic_terms(value: str, expected: str) -> None:
    from app.modules.literature_search.term_expansion import expand_term

    assert expand_term(value).core_term == expected


def test_builds_balanced_boolean_query_and_explains_operators() -> None:
    result = build_boolean_query(
        [
            SearchTermGroup(
                name="disease",
                core_term="Lung Neoplasms",
                terms=["lung cancer", "pulmonary neoplasm"],
            ),
            SearchTermGroup(name="target", core_term="EGFR", terms=["EGFR", "ERBB1"]),
        ]
    )

    assert result.boolean_query.count("(") == result.boolean_query.count(")")
    assert " OR " in result.boolean_query and " AND " in result.boolean_query
    assert any("OR" in item for item in result.explanations)
    assert any("AND" in item for item in result.explanations)


def test_rejects_chinese_and_illegal_pubmed_terms() -> None:
    with pytest.raises(ValueError, match="ASCII"):
        build_boolean_query(
            [SearchTermGroup(name="disease", core_term="x", terms=["胃癌"])]
        )
    with pytest.raises(ValueError, match="braces"):
        build_boolean_query(
            [SearchTermGroup(name="disease", core_term="x", terms=["EGFR{bad}"])]
        )


def test_user_can_remove_terms_before_query_building() -> None:
    result = build_boolean_query(
        [SearchTermGroup(name="drug", core_term="Aspirin", terms=["aspirin"])]
    )
    assert "acetylsalicylic acid" not in result.boolean_query
