"""Pure feasibility scoring and cross-candidate ranking sensitivity."""

from app.modules.feasibility.schema import (
    Confidence,
    DimensionName,
    DimensionScore,
    USER_DIMENSIONS,
)


def calculate_score(
    dimensions: list[DimensionScore],
) -> tuple[float, Confidence, list[DimensionName]]:
    """Calculate one-decimal weighted comparison score without inventing unknown inputs."""
    missing_inputs = [
        item.dimension
        for item in dimensions
        if item.dimension in USER_DIMENSIONS and item.score is None
    ]
    included = [item for item in dimensions if item.score is not None and item.weight > 0]
    if not included:
        raise ValueError("At least one positively weighted score is required")
    denominator = sum(item.weight for item in included)
    total_score = round(
        sum(item.weight * item.score for item in included if item.score is not None) / denominator,
        1,
    )
    confidence: Confidence = (
        "low" if len(missing_inputs) > 2 else "medium" if missing_inputs else "high"
    )
    return total_score, confidence, missing_inputs


def ranking_changed(before: dict[int, float], after: dict[int, float], direction_id: int) -> bool:
    """Return whether a direction's rank changes within the same comparable candidate set."""
    if set(before) != set(after) or direction_id not in before:
        return False
    rank_before = sorted(before, key=lambda item: (-before[item], item)).index(direction_id)
    rank_after = sorted(after, key=lambda item: (-after[item], item)).index(direction_id)
    return rank_before != rank_after


def rescore_dimensions(
    dimensions: list[DimensionScore],
    weights: dict[DimensionName, float],
) -> float:
    """Apply a common weight set to an existing dimension snapshot."""
    recalculated = [
        dimension.model_copy(update={"weight": weights[dimension.dimension]})
        for dimension in dimensions
    ]
    total_score, _, _ = calculate_score(recalculated)
    return total_score
