import csv
import io
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.feedback.model import Feedback
from app.modules.feedback.repository import FeedbackRepository
from app.modules.feedback.schema import FeedbackCreate, FeedbackRead


class FeedbackService:
    def __init__(self, session: AsyncSession):
        self.repo = FeedbackRepository(session)

    async def create(self, data: FeedbackCreate):
        entity = await self.repo.create(
            Feedback(
                task_completion_rate=data.task_completion_rate,
                useful=data.useful,
                citation_correct=data.citation_correct,
                data_correct=data.data_correct,
                error_type=data.error_type.value if data.error_type else None,
                comment=data.comment,
                next_step=data.next_step,
                created_at=datetime.now(UTC),
            )
        )
        return self._read(entity)

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Feedback not found: {id}")
        return self._read(entity)

    async def list(self):
        return [self._read(item) for item in await self.repo.list()]

    async def delete(self, id: int):
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"Feedback not found: {id}")
        await self.repo.delete(entity)

    async def anonymous_csv(self):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "task_completion_rate",
                "useful",
                "citation_correct",
                "data_correct",
                "error_type",
                "comment",
                "next_step",
                "created_at",
            ]
        )
        for item in await self.repo.list():
            writer.writerow(
                [
                    item.task_completion_rate,
                    item.useful,
                    item.citation_correct,
                    item.data_correct,
                    item.error_type,
                    item.comment,
                    item.next_step,
                    item.created_at.isoformat(),
                ]
            )
        return output.getvalue()

    @staticmethod
    def _read(entity):
        return FeedbackRead.model_validate(entity, from_attributes=True)
