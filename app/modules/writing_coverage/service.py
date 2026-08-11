"""Database boundary for writing publish-readiness checks."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.writing_ai.model import WritingAiSuggestion
from app.modules.writing_coverage.evaluator import evaluate_coverage
from app.modules.writing_coverage.schema import PublishReadinessRead
from app.modules.writing_project.service import WritingProjectService


class WritingCoverageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = WritingProjectService(session)

    async def check(self, project_id: int) -> PublishReadinessRead:
        project = await self._projects.get(project_id)
        statement = select(WritingAiSuggestion.id).where(
            WritingAiSuggestion.project_id == project_id,
            WritingAiSuggestion.confirmed_at.is_(None),
        )
        has_unconfirmed = (
            await self._session.execute(statement)
        ).scalar_one_or_none() is not None
        return evaluate_coverage(
            project.generated_content, project.evidence_references, has_unconfirmed
        )
