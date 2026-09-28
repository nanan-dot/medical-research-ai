"""论文工作活动记录。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.paper_library.model import PaperActivity


class PaperActivityService:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self.session = session
        self.actor_scope = actor_scope

    def record(
        self, item_id: int, kind: str, detail: str | None = None
    ) -> PaperActivity:
        activity = PaperActivity(
            library_item_id=item_id,
            actor_scope=self.actor_scope,
            kind=kind,
            detail=detail,
        )
        self.session.add(activity)
        return activity
