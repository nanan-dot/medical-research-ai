"""Orchestration for model-driven simulated reviews with strict evidence scope."""

import json
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, TemporarilyUnavailableError
from app.modules.ai_disclosure.event_normalizer import normalize_event
from app.modules.ai_disclosure.service import AIDisclosureService
from app.modules.writing_ai.service import WritingAiService
from app.modules.writing_project.service import WritingProjectService
from app.modules.writing_review.model import WritingReview
from app.modules.writing_review.roles import ROLE_CONSTRAINTS, RoleConstraint
from app.modules.writing_review.schema import (
    ReviewFinding,
    WritingReviewRead,
    WritingReviewRequest,
)

ReviewClient = Callable[[str], Awaitable[str]]


class WritingReviewService:
    def __init__(
        self, session: AsyncSession, client: ReviewClient | None = None
    ) -> None:
        self._session = session
        self._projects = WritingProjectService(session)
        self._writing_ai = WritingAiService(session)
        self._client = client

    async def review(
        self, project_id: int, request: WritingReviewRequest
    ) -> WritingReviewRead:
        project = await self._projects.get(project_id)
        if project.version != request.expected_version:
            raise ConflictError("Writing project version conflict; reload and retry")
        self._validate_scope(project, request)
        config = await self._writing_ai._resolve_config(request.model_config_id)
        constraint = self._constraint(request)
        try:
            findings = await self._generate_findings(
                self._prompt(project, request, constraint), config
            )
        except Exception as error:
            raise TemporarilyUnavailableError(
                "Review model failed; no simulated review was saved"
            ) from error
        review = WritingReview(
            project_id=project_id,
            simulated=True,
            reviewer_label=constraint.title,
            findings_json=json.dumps(
                [item.model_dump() for item in findings], ensure_ascii=False
            ),
        )
        self._session.add(review)
        await self._session.flush()
        await AIDisclosureService(self._session).add_event(
            project_id,
            normalize_event(
                model_name=config.model_name,
                model_version=config.model_name,
                purpose="analysis",
                input_scope={"papers": len(request.evidence_reference_ids)},
                output_version=f"writing-review:{review.id}",
                human_edited=False,
                is_cloud=config.provider != "ollama",
            ),
        )
        await self._session.refresh(review)
        return self._read(review)

    async def _generate_findings(self, prompt: str, config) -> list[ReviewFinding]:
        response = (
            await self._client(prompt)
            if self._client is not None
            else await self._writing_ai.generate_text(prompt, config)
        )
        payload = json.loads(response)
        return [ReviewFinding.model_validate(item) for item in payload]

    @staticmethod
    def _validate_scope(project, request: WritingReviewRequest) -> None:
        segment_ids = {item.id for item in project.generated_content.segments}
        reference_ids = {item.id for item in project.evidence_references}
        if not set(request.segment_ids).issubset(segment_ids) or not set(
            request.evidence_reference_ids
        ).issubset(reference_ids):
            raise ConflictError(
                "Review scope must be explicitly selected from project segments and evidence references"
            )

    @staticmethod
    def _constraint(request: WritingReviewRequest) -> RoleConstraint:
        if request.role is not None:
            return ROLE_CONSTRAINTS[request.role]
        custom = request.custom_reviewer
        assert custom is not None
        return RoleConstraint(
            f"模拟自定义评审者：{custom.identity}",
            custom.expertise,
            "仅评审用户选定文本与证据",
            custom.limitations,
        )

    @staticmethod
    def _prompt(
        project, request: WritingReviewRequest, constraint: RoleConstraint
    ) -> str:
        selected = [
            item.model_dump()
            for item in project.generated_content.segments
            if item.id in request.segment_ids
        ]
        return json.dumps(
            {
                "simulated": True,
                "role": constraint.__dict__,
                "segments": selected,
                "evidence_reference_ids": request.evidence_reference_ids,
                "output": "JSON array: severity, segment_id, issue, rationale, evidence_status, recommendation. Do not invent sources or facts.",
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _read(entity: WritingReview) -> WritingReviewRead:
        return WritingReviewRead(
            id=entity.id,
            project_id=entity.project_id,
            simulated=True,
            reviewer_label=entity.reviewer_label,
            findings=[
                ReviewFinding.model_validate(item)
                for item in json.loads(entity.findings_json)
            ],
            created_at=entity.created_at,
        )
