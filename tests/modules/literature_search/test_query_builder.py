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
