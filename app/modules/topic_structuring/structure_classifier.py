"""Pure guards that prevent an invalid PICO/PECO template from reaching users."""

from typing import Literal

StructuringStatus = Literal["pico", "peco", "mechanism", "unstructured"]


def classify_structuring_status(
    requested_status: str,
    *,
    disease: str | None,
    target: str | None,
    intervention: str | None,
    mechanism: str | None,
    comparator: str | None,
    outcome: str | None,
) -> StructuringStatus:
    """Return a defensible structure type, downgrading incomplete templates to unstructured."""
    has_population = bool(disease or target)
    has_exposure = bool(intervention or mechanism)
    has_mechanism = bool(target or mechanism)
    has_outcome = bool(outcome)

    if requested_status == "pico" and has_population and has_exposure and has_outcome:
        return "pico"
    if (
        requested_status == "peco"
        and has_population
        and has_exposure
        and comparator
        and has_outcome
    ):
        return "peco"
    if requested_status == "mechanism" and has_mechanism:
        return "mechanism"
    return "unstructured"
