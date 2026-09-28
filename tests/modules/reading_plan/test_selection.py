from app.modules.reading_plan.selection import (
    SelectionCandidate,
    allocate_core_quotas,
    select_reading_plan,
)


def _candidate(position: int, publication_type: str = "Journal Article") -> SelectionCandidate:
    return SelectionCandidate(
        pmid=str(40_000_000 + position),
        position=position,
        year=2026 - (position % 8),
        publication_types=(publication_type,),
        has_abstract=position % 2 == 0,
        mesh_match_count=position % 3,
    )


def test_ac_rp_01_500_items_select_default_12_and_four_stages() -> None:
    types = (
        "Systematic Review",
        "Practice Guideline",
        "Randomized Controlled Trial",
        "Journal Article",
    )
    candidates = [_candidate(index, types[index % 4]) for index in range(500)]

    selected = select_reading_plan(candidates, target_core_count=12)

    assert len([item for item in selected if item.role == "core"]) == 12
    assert {item.stage for item in selected} == {
        "overview", "clinical_decision", "primary_evidence", "frontier"
    }


def test_ac_rp_03_deterministic_quota_redistribution() -> None:
    candidates = [_candidate(index, "Randomized Controlled Trial") for index in range(11)]
    selected = select_reading_plan(candidates, target_core_count=10)
    assert len([item for item in selected if item.role == "core"]) == 10
    assert allocate_core_quotas(candidates, 10) == allocate_core_quotas(candidates, 10)


def test_ac_rp_04_selection_is_deterministic_with_stable_ties() -> None:
    candidates = [_candidate(index, "Review") for index in range(20)]
    first = select_reading_plan(candidates, target_core_count=10)
    second = select_reading_plan(list(reversed(candidates)), target_core_count=10)
    assert [(item.pmid, item.role) for item in first] == [
        (item.pmid, item.role) for item in second
    ]


def test_ac_rp_05_items_are_unique_and_roles_exclusive() -> None:
    selected = select_reading_plan([_candidate(index) for index in range(15)], 10)
    assert len({item.pmid for item in selected}) == len(selected)


def test_ac_rp_06_highly_relevant_is_not_public_stage() -> None:
    selected = select_reading_plan([_candidate(index) for index in range(15)], 10)
    assert all(item.stage != "highly_relevant" for item in selected)


def test_ac_rp_07_missing_metrics_are_unavailable_not_zero() -> None:
    item = select_reading_plan([_candidate(index) for index in range(10)], 10)[0]
    assert item.evidence_features["article_metrics"]["status"] == "not_collected"
    assert item.evidence_features["journal_metrics"]["value"] is None
