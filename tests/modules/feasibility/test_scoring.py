"""Pure feasibility scoring tests."""

import pytest

from app.modules.feasibility.schema import DimensionScore
from app.modules.feasibility.scoring import calculate_score, ranking_changed


def _score(
    dimension: str,
    value: float | None,
    weight: float = 1,
    source: str = "system",
) -> DimensionScore:
    return DimensionScore(
        dimension=dimension,
        score=value,
        weight=weight,
        basis="Test basis",
        score_source=source,
    )


def test_weighted_score_and_missing_confidence() -> None:
    total, confidence, missing = calculate_score(
        [
            _score("literature_base", 80, 2),
            _score("sample_availability", None, source="unknown"),
            _score("data_availability", None, source="unknown"),
            _score("timeline", None, source="unknown"),
        ]
    )

    assert total == 80
    assert confidence == "low"
    assert len(missing) == 3


def test_zero_weights_are_excluded() -> None:
    total, _, _ = calculate_score(
        [
            _score("literature_base", 80, 0),
            _score("technical_feasibility", 60),
        ]
    )

    assert total == 60
    with pytest.raises(ValueError):
        calculate_score([_score("literature_base", 80, 0)])


def test_cross_candidate_rank_change_is_detected() -> None:
    assert ranking_changed({1: 60, 2: 70}, {1: 80, 2: 70}, 1)
    assert not ranking_changed({1: 60, 2: 70}, {1: 60, 2: 70}, 1)
