"""Unit tests for the pure template guard."""

import pytest

from app.modules.topic_structuring.structure_classifier import classify_structuring_status


@pytest.mark.parametrize(
    ("requested_status", "values", "expected"),
    [
        ("pico", ("diabetes", None, "metformin", None, None, "HbA1c"), "pico"),
        ("peco", ("workers", None, "air pollution", None, "low exposure", "asthma"), "peco"),
        ("mechanism", (None, "EGFR", None, "signaling", None, None), "mechanism"),
        ("pico", ("diabetes", None, None, None, None, None), "unstructured"),
    ],
)
def test_classify_status_only_accepts_complete_templates(
    requested_status: str, values: tuple[str | None, ...], expected: str
) -> None:
    disease, target, intervention, mechanism, comparator, outcome = values
    assert classify_structuring_status(
        requested_status,
        disease=disease,
        target=target,
        intervention=intervention,
        mechanism=mechanism,
        comparator=comparator,
        outcome=outcome,
    ) == expected
