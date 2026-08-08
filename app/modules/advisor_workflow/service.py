"""Advisor review orchestration with explicit private-data model routing."""

import json
from datetime import UTC, datetime
from typing import cast

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.advisor_workflow.model import AdvisorReview, DirectionRevision
from app.modules.advisor_workflow.mock_reviewer import MockReviewGenerator
from app.modules.advisor_workflow.repository import AdvisorWorkflowRepository
from app.modules.advisor_workflow.schema import (
    AdvisorNoteCreate,
    AdvisorReviewRead,
    DirectionVersionRead,
    Decision,
    ReviewerType,
    MockReviewRequest,
)
from app.modules.advisor_workflow.state_machine import status_for_decision
from app.modules.research_direction.model import ResearchDirection

class AdvisorWorkflowService:
    def __init__(self, session, mock_generator: MockReviewGenerator | None = None) -> None:
        self._repository = AdvisorWorkflowRepository(session)
        self._mock_generator = mock_generator or MockReviewGenerator(session)

    async def record_note(
        self, direction_id: int, payload: AdvisorNoteCreate, reviewer_type: str = "real"
    ) -> AdvisorReviewRead:
        direction = await self._direction(direction_id)
        direction.status = status_for_decision(direction.status, payload.decision)
        review = AdvisorReview(
            direction_id=direction_id,
            reviewer_type=reviewer_type,
            decision=payload.decision,
            summary=payload.summary,
            points_json=json.dumps([point.model_dump() for point in payload.points]),
            literature_gaps_json=json.dumps(
                [item.model_dump() for item in payload.literature_gaps]
            ),
            experiment_conditions_json=json.dumps(
                [item.model_dump() for item in payload.experiment_conditions]
            ),
        )
        await self._repository.save_direction(direction)
        return self._to_review(await self._repository.create_review(review))

    async def mock_review(
        self, direction_id: int, request: MockReviewRequest
    ) -> AdvisorReviewRead:
        direction = await self._direction(direction_id)
        payload = await self._mock_generator.generate(
            direction,
            provider=request.provider,
            model_config_id=request.model_config_id,
        )
        return await self.record_note(direction_id, payload, reviewer_type="mock")

    async def list_notes(self, direction_id: int) -> list[AdvisorReviewRead]:
        await self._direction(direction_id)
        return [
            self._to_review(review) for review in await self._repository.list_reviews(direction_id)
        ]

    async def revise(self, direction_id: int, review_id: int) -> DirectionVersionRead:
        direction = await self._direction(direction_id)
        reviews = await self._repository.list_reviews(direction_id)
        review = next((item for item in reviews if item.id == review_id), None)
        if review is None:
            raise NotFoundError(f"Advisor review not found: {review_id}")
        if review.decision != "revise":
            raise ConflictError("Only a revise decision can create a revision")
        status_for_decision(direction.status, "revise")
        revisions = await self._repository.list_revisions(direction_id)
        snapshot = self._snapshot(direction)
        parent_id = revisions[-1].id if revisions else None
        await self._repository.create_revision(
            DirectionRevision(
                direction_id=direction_id,
                version=direction.version,
                revision_parent_id=parent_id,
                snapshot_json=json.dumps(snapshot),
            )
        )
        direction.version += 1
        direction.status = "active"
        direction.updated_at = datetime.now(UTC)
        await self._repository.save_direction(direction)
        return self._current_version(direction, parent_id)

    async def versions(self, direction_id: int) -> list[DirectionVersionRead]:
        direction = await self._direction(direction_id)
        revisions = await self._repository.list_revisions(direction_id)
        result = [
            DirectionVersionRead(
                id=item.id,
                direction_id=item.direction_id,
                version=item.version,
                revision_parent_id=item.revision_parent_id,
                snapshot=json.loads(item.snapshot_json),
                created_at=item.created_at,
            )
            for item in revisions
        ]
        result.append(self._current_version(direction, revisions[-1].id if revisions else None))
        return result

    async def export_markdown(self, direction_id: int) -> str:
        direction = await self._direction(direction_id)
        reviews = await self.list_notes(direction_id)
        reviewed = "Pending advisor confirmation" if not reviews else reviews[-1].decision
        return f"# Advisor discussion report\n\nGenerated at: {datetime.now(UTC).isoformat()}\nVersion: {direction.version}\n\n## Candidate\n\n- Name: {direction.name}\n- Question: {direction.question}\n- Evidence: {direction.current_evidence}\n- Risks: {direction.ethics_risk or direction.resource_risk or 'Not specified'}\n- Advisor status: {reviewed}\n"

    async def _direction(self, direction_id: int) -> ResearchDirection:
        direction = await self._repository.get_direction(direction_id)
        if direction is None:
            raise NotFoundError(f"Research direction not found: {direction_id}")
        return direction

    @staticmethod
    def _snapshot(direction: ResearchDirection) -> dict[str, object]:
        return {
            column.name: getattr(direction, column.name)
            for column in direction.__table__.columns
            if column.name not in {"created_at", "updated_at"}
        }

    @staticmethod
    def _current_version(
        direction: ResearchDirection, parent_id: int | None
    ) -> DirectionVersionRead:
        return DirectionVersionRead(
            id=None,
            direction_id=direction.id,
            version=direction.version,
            revision_parent_id=parent_id,
            snapshot=AdvisorWorkflowService._snapshot(direction),
            created_at=direction.updated_at,
        )

    @staticmethod
    def _to_review(review: AdvisorReview) -> AdvisorReviewRead:
        return AdvisorReviewRead(
            id=review.id,
            direction_id=review.direction_id,
            reviewer_type=cast(ReviewerType, review.reviewer_type),
            decision=cast(Decision, review.decision),
            summary=review.summary,
            points=json.loads(review.points_json),
            literature_gaps=json.loads(review.literature_gaps_json),
            experiment_conditions=json.loads(review.experiment_conditions_json),
            is_ai_simulation=review.reviewer_type == "mock",
            created_at=review.created_at,
        )
