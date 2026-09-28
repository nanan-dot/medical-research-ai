"""Composition layer for the bounded paper-research center projection."""

import base64
import binascii
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError, UnprocessableEntityError
from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.paper_research.center_repository import CenterRepository
from app.modules.paper_research.center_schema import (
    ActivityPage,
    ActivityRead,
    CenterRead,
    CenterSummaryRead,
    ContinueTaskRead,
    CurrentContextRead,
    CurrentContextStageUpdate,
    CurrentContextUpdate,
    NextActionRead,
    RecentPaperRead,
    ResearchStage,
)
from app.modules.paper_research.next_action import decide_next_action


class CenterService:
    """Coordinate source projections and explicit user state without duplicating facts."""

    def __init__(
        self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE
    ) -> None:
        self.session = session
        self.actor_scope = actor_scope
        self.repository = CenterRepository(session)

    async def current_context(self) -> CurrentContextRead | None:
        row = await self.repository.preference(self.actor_scope)
        return self._context_read(row) if row else None

    async def set_context(self, payload: CurrentContextUpdate) -> CurrentContextRead:
        if (
            payload.research_context_id is not None
            and not await self.repository.context_exists(payload.research_context_id)
        ):
            raise NotFoundError("研究项目不存在")
        row = await self.repository.preference(self.actor_scope)
        if row is None:
            if payload.expected_version != 1:
                raise ConflictError("当前研究已被修改")
            preference = await self.repository.create_preference(
                self.actor_scope, payload.research_context_id, payload.stage.value
            )
        else:
            preference, _ = row
            if not await self.repository.update_preference(
                preference,
                payload.expected_version,
                context_id=payload.research_context_id,
                stage=payload.stage.value,
                replace_context=True,
            ):
                raise ConflictError("当前研究已被修改")
            await self.session.flush()
            preference = (await self.repository.preference(self.actor_scope))[0]
        name = None
        if preference.research_context_id:
            current = await self.repository.preference(self.actor_scope)
            name = current[1] if current else None
        return CurrentContextRead(
            research_context_id=preference.research_context_id,
            research_name=name,
            stage=ResearchStage(preference.stage),
            version=preference.version,
        )

    async def update_stage(
        self, payload: CurrentContextStageUpdate
    ) -> CurrentContextRead:
        row = await self.repository.preference(self.actor_scope)
        if row is None:
            raise NotFoundError("尚未选择当前研究")
        preference, _ = row
        if not await self.repository.update_preference(
            preference, payload.expected_version, stage=payload.stage.value
        ):
            raise ConflictError("当前研究已被修改")
        await self.session.flush()
        return await self.current_context()  # type: ignore[return-value]

    async def center(
        self, continue_limit: int, activity_limit: int, recent_limit: int
    ) -> CenterRead:
        context = await self.current_context()
        rows = await self.repository.work_rows(
            context.research_context_id if context else None, self.actor_scope
        )
        tasks = [self._task(*row) for row in rows]
        tasks.sort(
            key=lambda task: (
                self._rank(task),
                -(task.last_work_at.timestamp() if task.last_work_at else 0),
                task.paper_item_id,
            )
        )
        activities = [
            self._activity(row)
            for row in await self.repository.activities(
                self.actor_scope, None, activity_limit
            )
        ]
        papers = [self._paper(*row) for row in rows]
        papers.sort(
            key=lambda paper: (
                -(paper.last_work_at.timestamp() if paper.last_work_at else 0),
                paper.paper_item_id,
            )
        )
        counts = await self.repository.summary()
        pending_fields = sum(
            len(self._json_list(value))
            for value in await self.repository.pending_confirmation_values()
        )
        return CenterRead(
            current_research=context,
            continue_tasks=tasks[:continue_limit],
            recent_activities=activities,
            recent_papers=papers[:recent_limit],
            summary=CenterSummaryRead(
                papers=counts[0],
                reading=counts[1],
                deep_reading=counts[2],
                completed=counts[3],
                pending_confirmation_items=counts[4],
                pending_confirmation_fields=pending_fields,
            ),
            capabilities={
                "current_research_selection": "available",
                "exact_reader_resume": "available",
                "next_action_rules": "available",
                "ai_task_planning": "unavailable",
            },
        )

    async def activity_page(self, cursor: str | None, limit: int) -> ActivityPage:
        decoded = self._decode_cursor(cursor) if cursor else None
        rows = await self.repository.activities(self.actor_scope, decoded, limit + 1)
        items = [self._activity(row) for row in rows[:limit]]
        next_cursor = (
            self._cursor(rows[limit - 1][0].created_at, rows[limit - 1][0].id)
            if len(rows) > limit
            else None
        )
        return ActivityPage(items=items, next_cursor=next_cursor)

    @staticmethod
    def _context_read(row) -> CurrentContextRead:
        preference, name = row
        return CurrentContextRead(
            research_context_id=preference.research_context_id,
            research_name=name,
            stage=ResearchStage(preference.stage),
            version=preference.version,
        )

    @staticmethod
    def _json_list(value: str | None) -> list[str]:
        try:
            parsed = json.loads(value or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def _task(self, item, state, analysis, reader) -> ContinueTaskRead:
        reading_status = state.reading_status if state else "unread"
        pending = self._json_list(analysis.pending_confirmations) if analysis else []
        can_read = item.document_id is not None and item.fulltext_status in {
            "local_pdf_available",
            "open_fulltext_available",
        }
        target = None
        if reader and reader.document_file_hash:
            target = {
                "item_id": item.id,
                "session_id": reader.id,
                "page": reader.last_page,
                "offset": reader.viewport_offset_ratio,
            }
        decision = decide_next_action(
            pending_fields=len(pending),
            analysis_status=analysis.analysis_status if analysis else None,
            reading_status=reading_status,
            can_read=can_read,
            can_analyze=item.document_id is not None,
            reader_target=target,
            section=state.current_section if state else None,
            item_id=item.id,
        )
        task_names = self._json_list(analysis.task_names_json) if analysis else []
        completed = (
            self._json_list(analysis.completed_task_names_json) if analysis else []
        )
        mode = (
            "confirmation"
            if pending
            else "deep_reading"
            if analysis and analysis.analysis_status in {"pending", "analyzing"}
            else "reading"
        )
        last_work = max(
            (
                value
                for value in (
                    (state.last_read_at if state else None),
                    (state.last_analysis_at if state else None),
                )
                if value is not None
            ),
            default=None,
        )
        next_action = NextActionRead(
            kind=decision.kind,
            title=decision.title,
            description=decision.description,
            reason_codes=decision.reason_codes,
            target=decision.target,
            is_available=decision.is_available,
            unavailable_reason=decision.unavailable_reason,
        )
        return ContinueTaskRead(
            paper_item_id=item.id,
            title=item.title,
            journal=item.journal,
            year=item.year,
            work_mode=mode,
            current_section=state.current_section if state else None,
            reading_progress_percent=state.reading_progress_percent if state else 0,
            analysis_completed=len(completed),
            analysis_total=len(task_names),
            last_work_at=last_work,
            entry_available=decision.is_available,
            next_action=next_action,
            sort_reason=decision.reason_codes[0],
        )

    @staticmethod
    def _rank(task: ContinueTaskRead) -> int:
        return {"confirmation": 0, "deep_reading": 1, "reading": 2}.get(
            task.work_mode, 3
        )

    @staticmethod
    def _paper(item, state, analysis, reader) -> RecentPaperRead:
        last_work_at = max(
            (
                value
                for value in (
                    state.last_read_at if state else None,
                    state.last_analysis_at if state else None,
                )
                if value is not None
            ),
            default=None,
        )
        return RecentPaperRead(
            paper_item_id=item.id,
            title=item.title,
            journal=item.journal,
            year=item.year,
            reading_status=state.reading_status if state else "unread",
            entry_available=item.document_id is not None,
            last_work_at=last_work_at,
        )

    @staticmethod
    def _activity(row) -> ActivityRead:
        activity, item, relation, name = row
        return ActivityRead(
            id=activity.id,
            kind=activity.kind,
            occurred_at=activity.created_at,
            paper_item_id=item.id,
            paper_title=item.title,
            research_context_id=relation.research_context_id if relation else None,
            research_name=name,
            target={"item_id": item.id},
            summary=activity.detail,
            target_available=True,
            unavailable_reason=None,
        )

    @staticmethod
    def _cursor(created_at: datetime, activity_id: int) -> str:
        return base64.urlsafe_b64encode(
            f"{created_at.isoformat()}|{activity_id}".encode()
        ).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, int]:
        try:
            timestamp, identifier = (
                base64.urlsafe_b64decode(cursor.encode()).decode().rsplit("|", 1)
            )
            return datetime.fromisoformat(timestamp), int(identifier)
        except (binascii.Error, ValueError, UnicodeDecodeError) as error:
            raise UnprocessableEntityError("活动游标无效") from error
