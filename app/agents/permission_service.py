"""项目成员和专业资质门禁。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.confirmation_model import (
    AgentRoleQualificationRecord,
    ResearchContextMembershipRecord,
)
from app.agents.errors import PermissionDeniedError

LOCAL_OWNER = "local-owner"


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class PermissionService:
    async def require_membership(
        self, session: AsyncSession, research_context_id: str, actor_scope: str
    ) -> ResearchContextMembershipRecord:
        membership = await session.scalar(
            select(ResearchContextMembershipRecord).where(
                ResearchContextMembershipRecord.research_context_id
                == research_context_id,
                ResearchContextMembershipRecord.actor_scope == actor_scope,
                ResearchContextMembershipRecord.status == "active",
            )
        )
        if membership is None:
            raise PermissionDeniedError()
        return membership

    async def require_qualification(
        self, session: AsyncSession, actor_scope: str, role: str
    ) -> AgentRoleQualificationRecord:
        now = datetime.now(UTC)
        qualification = await session.scalar(
            select(AgentRoleQualificationRecord).where(
                AgentRoleQualificationRecord.actor_scope == actor_scope,
                AgentRoleQualificationRecord.authorized_role == role,
                AgentRoleQualificationRecord.status == "active",
            )
        )
        if (
            qualification is None
            or (
                qualification.valid_from is not None
                and _as_utc(qualification.valid_from) > now
            )
            or (
                qualification.valid_until is not None
                and _as_utc(qualification.valid_until) <= now
            )
        ):
            raise PermissionDeniedError("required qualification is not active")
        return qualification
