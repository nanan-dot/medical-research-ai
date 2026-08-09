"""证据驱动写作服务：只校验和保存用户/模型提供的内容，不生成医学事实。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.modules.evidence_writing.polish_guard import validate_polish
from app.modules.evidence_writing.schema import (
    DraftRequest,
    OutlineRequest,
    PolishRequest,
)
from app.modules.evidence_writing.sentence_marker import validate_segments
from app.modules.evidence_writing.state_machine import transition
from app.modules.writing_project.schema import WritingProjectRead, WritingProjectUpdate
from app.modules.writing_project.service import WritingProjectService


class EvidenceWritingService:
    def __init__(self, session: AsyncSession) -> None:
        self.projects = WritingProjectService(session)

    async def _update_and_snapshot(
        self, project_id: int, content, expected_version: int
    ) -> WritingProjectRead:
        updated = await self.projects.update(
            project_id,
            WritingProjectUpdate(
                generated_content=content, expected_version=expected_version
            ),
        )
        await self.projects.save_version(project_id, expected_version=updated.version)
        return updated

    async def submit_outline(
        self, project_id: int, request: OutlineRequest
    ) -> WritingProjectRead:
        project = await self.projects.get(project_id)
        next_state = transition(
            project.generated_content.workflow_state, "submit_outline"
        )
        if request.confirmed:
            next_state = transition(next_state, "confirm_outline")
        content = request.content.model_copy(update={"workflow_state": next_state})
        return await self._update_and_snapshot(
            project_id, content, request.expected_version
        )

    async def generate_draft(
        self, project_id: int, request: DraftRequest
    ) -> WritingProjectRead:
        project = await self.projects.get(project_id)
        try:
            next_state = transition(
                project.generated_content.workflow_state, "generate_draft"
            )
        except ValueError as error:
            raise ConflictError(
                "Outline must be confirmed before draft generation"
            ) from error
        pending_ids = {item.id for item in request.content.pending_items}
        validate_segments(
            [segment.model_dump() for segment in request.content.segments],
            pending_item_ids=pending_ids,
        )
        content = request.content.model_copy(update={"workflow_state": next_state})
        return await self._update_and_snapshot(
            project_id, content, request.expected_version
        )

    async def edit_draft(
        self, project_id: int, request: DraftRequest
    ) -> WritingProjectRead:
        project = await self.projects.get(project_id)
        next_state = transition(
            project.generated_content.workflow_state, "start_editing"
        )
        content = request.content.model_copy(update={"workflow_state": next_state})
        return await self._update_and_snapshot(
            project_id, content, request.expected_version
        )

    async def polish(
        self, project_id: int, request: PolishRequest
    ) -> WritingProjectRead:
        project = await self.projects.get(project_id)
        polishing_state = transition(
            project.generated_content.workflow_state, "start_polishing"
        )
        original = " ".join(
            segment.text for segment in project.generated_content.segments
        )
        polished = " ".join(segment.text for segment in request.content.segments)
        validate_polish(original, polished)
        original_user = [
            s.text
            for s in project.generated_content.segments
            if s.origin == "user_provided"
        ]
        polished_user = [
            s.text for s in request.content.segments if s.origin == "user_provided"
        ]
        if original_user != polished_user:
            raise ValueError("user_provided content cannot be changed during polishing")
        done_state = transition(polishing_state, "finish")
        content = request.content.model_copy(update={"workflow_state": done_state})
        return await self._update_and_snapshot(
            project_id, content, request.expected_version
        )
