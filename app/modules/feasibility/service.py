"""Application service for evidence-grounded feasibility comparisons."""

import json
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.feasibility.model import FeasibilityScore, FeasibilityWeightProfile
from app.modules.feasibility.repository import FeasibilityRepository
from app.modules.feasibility.schema import (
    DimensionName,
    DimensionScore,
    Confidence,
    FeasibilityRead,
    FeasibilityRequest,
    UserAssessment,
)
from app.modules.feasibility.scoring import (
    calculate_score,
    ranking_changed,
    rescore_dimensions,
)

DEFAULT_WEIGHTS: dict[DimensionName, float] = {
    "literature_base": 1.0,
    "novelty_uncertainty": 1.0,
    "technical_feasibility": 1.0,
    "sample_availability": 1.0,
    "data_availability": 1.0,
    "timeline": 1.0,
    "budget": 1.0,
    "ethics": 1.0,
    "analysis_difficulty": 1.0,
    "advisor_alignment": 1.0,
}


class FeasibilityService:
    """Create versioned scores without inferring user-only operational inputs."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = FeasibilityRepository(session)

    async def score(
        self,
        direction_id: int,
        payload: FeasibilityRequest,
    ) -> FeasibilityRead:
        """Create an initial score using default weights plus request overrides."""
        return await self._save_score(
            direction_id=direction_id,
            requested_weights=payload.weights,
            assessments=payload.user_assessments,
            detect_ranking_change=False,
        )

    async def rescore_with_weights(
        self,
        direction_id: int,
        weights: dict[DimensionName, float],
    ) -> FeasibilityRead:
        """Create a version that inherits the prior user self-assessments.

        This PATCH intentionally accepts weights only. It cannot overwrite the
        prior assessment snapshot, so version provenance remains explicit.
        """
        versions = await self._repository.list_versions(direction_id)
        if not versions:
            raise ConflictError("Create an initial feasibility score before adjusting weights")
        previous = self._read(versions[-1])
        assessments = [
            UserAssessment(
                dimension=dimension.dimension,
                score=dimension.score,
                basis=dimension.basis,
            )
            for dimension in previous.dimensions
            if dimension.score_source == "user"
        ]
        return await self._save_score(
            direction_id=direction_id,
            requested_weights=weights,
            assessments=assessments,
            detect_ranking_change=True,
        )

    async def versions(self, direction_id: int) -> list[FeasibilityRead]:
        """Return immutable score snapshots ordered by version."""
        return [self._read(score) for score in await self._repository.list_versions(direction_id)]

    async def _save_score(
        self,
        *,
        direction_id: int,
        requested_weights: dict[DimensionName, float] | None,
        assessments: Sequence[UserAssessment],
        detect_ranking_change: bool,
    ) -> FeasibilityRead:
        direction = await self._repository.get_direction(direction_id)
        if direction is None:
            raise NotFoundError(f"Research direction not found: {direction_id}")

        default_weights = await self._default_weights()
        weights = {**default_weights, **(requested_weights or {})}
        self._validate_weights(weights)
        dimensions = self._build_dimensions(direction, weights, assessments)
        total_score, confidence, missing_inputs = calculate_score(dimensions)
        if len(missing_inputs) == 5:
            raise ConflictError("All user-assessment dimensions are unknown")

        prior_versions = await self._repository.list_versions(direction_id)
        ranking_sensitive = False
        if detect_ranking_change:
            ranking_sensitive = await self._ranking_changed(
                evidence_matrix_id=direction.evidence_matrix_id,
                direction_id=direction_id,
                new_weights=weights,
                new_total_score=total_score,
            )

        score = FeasibilityScore(
            direction_id=direction_id,
            version=len(prior_versions) + 1,
            dimensions_json=json.dumps(
                [dimension.model_dump() for dimension in dimensions],
                ensure_ascii=False,
            ),
            weights_json=json.dumps(weights, ensure_ascii=False),
            total_score=total_score,
            confidence=confidence,
            missing_inputs_json=json.dumps(missing_inputs, ensure_ascii=False),
            ranking_sensitive=ranking_sensitive,
        )
        return self._read(await self._repository.create_score(score))

    async def _default_weights(self) -> dict[DimensionName, float]:
        profile = await self._repository.get_default_profile()
        if profile is None:
            profile = await self._repository.create_profile(
                FeasibilityWeightProfile(
                    name="Default equal weights",
                    weights_json=json.dumps(DEFAULT_WEIGHTS),
                    rationale="Initial equal weighting across all ten dimensions.",
                    is_default=True,
                )
            )
        return json.loads(profile.weights_json)

    async def _ranking_changed(
        self,
        *,
        evidence_matrix_id: int,
        direction_id: int,
        new_weights: dict[DimensionName, float],
        new_total_score: float,
    ) -> bool:
        comparable_scores = await self._repository.list_latest_scores_for_matrix(evidence_matrix_id)
        if len(comparable_scores) < 2:
            return False

        before = {score.direction_id: score.total_score for score in comparable_scores}
        after = {
            score.direction_id: rescore_dimensions(
                self._read(score).dimensions,
                new_weights,
            )
            for score in comparable_scores
        }
        after[direction_id] = new_total_score
        return ranking_changed(before, after, direction_id)

    @staticmethod
    def _validate_weights(weights: dict[DimensionName, float]) -> None:
        if any(weight < 0 for weight in weights.values()):
            raise ConflictError("Weights cannot be negative")
        if not any(weights.values()):
            raise ConflictError("Weights must contain a positive value")

    @staticmethod
    def _build_dimensions(
        direction: Any,
        weights: dict[DimensionName, float],
        assessments: Sequence[UserAssessment],
    ) -> list[DimensionScore]:
        user_scores = {assessment.dimension: assessment for assessment in assessments}
        evidence_count = len(json.loads(direction.evidence_json))
        system_dimensions: dict[DimensionName, tuple[float, str]] = {
            "literature_base": (
                min(100, evidence_count * 25),
                "Evidence matrix source count.",
            ),
            "novelty_uncertainty": (
                50,
                "Comparison-only uncertainty indicator, not a publication prediction.",
            ),
            "technical_feasibility": (
                60 if direction.methods else 40,
                "Whether a method is already specified.",
            ),
            "analysis_difficulty": (60, "Requires supervisor review."),
            "advisor_alignment": (
                50,
                "Neutral default; it does not infer supervisor commitment.",
            ),
        }
        dimensions: list[DimensionScore] = []
        for dimension, weight in weights.items():
            system_score = system_dimensions.get(dimension)
            if system_score is not None:
                score, basis = system_score
                dimensions.append(
                    DimensionScore(
                        dimension=dimension,
                        score=score,
                        weight=weight,
                        basis=basis,
                        score_source="system",
                    )
                )
                continue

            assessment = user_scores.get(dimension)
            dimensions.append(
                DimensionScore(
                    dimension=dimension,
                    score=assessment.score if assessment else None,
                    weight=weight,
                    basis=(
                        assessment.basis
                        if assessment and assessment.basis
                        else "Not provided; excluded from the weighted score."
                    ),
                    score_source=(
                        "user"
                        if assessment is not None and assessment.score is not None
                        else "unknown"
                    ),
                )
            )
        return dimensions

    @staticmethod
    def _read(entity: FeasibilityScore) -> FeasibilityRead:
        return FeasibilityRead(
            id=entity.id,
            direction_id=entity.direction_id,
            version=entity.version,
            dimensions=[
                DimensionScore.model_validate(dimension)
                for dimension in json.loads(entity.dimensions_json)
            ],
            weights=json.loads(entity.weights_json),
            total_score=entity.total_score,
            confidence=cast(Confidence, entity.confidence),
            missing_inputs=json.loads(entity.missing_inputs_json),
            ranking_sensitive=entity.ranking_sensitive,
            created_at=entity.created_at,
        )
