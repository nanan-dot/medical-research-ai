"""Persistence boundary for recommendation V5 run selection."""

import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recommendation.model import (
    RecommendationNarrationLease,
    RecommendationRun,
)

NarrationLeaseAction = Literal["claimed", "cached", "busy"]


def _as_utc(value: datetime) -> datetime:
    """SQLite returns timezone-naive values even for timezone-aware columns."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_fingerprint(
        self, result_id: int, fingerprint: str
    ) -> RecommendationRun | None:
        return (
            await self.session.execute(
                select(RecommendationRun).where(
                    RecommendationRun.source_result_id == result_id,
                    RecommendationRun.input_fingerprint == fingerprint,
                )
            )
        ).scalar_one_or_none()

    async def get_run(self, run_id: int) -> RecommendationRun | None:
        return await self.session.get(RecommendationRun, run_id)

    async def claim_queued(self, run_id: int) -> bool:
        now = datetime.now(UTC)
        result = await self.session.execute(
            update(RecommendationRun)
            .where(
                RecommendationRun.id == run_id,
                RecommendationRun.status == "queued",
                RecommendationRun.cancel_requested.is_(False),
            )
            .values(status="running", started_at=now, heartbeat_at=now)
        )
        return bool(getattr(result, "rowcount", 0))

    async def list_recoverable(
        self, *, stale_after: timedelta = timedelta(minutes=5)
    ) -> list[RecommendationRun]:
        stale_before = datetime.now(UTC) - stale_after
        return list(
            (
                await self.session.execute(
                    select(RecommendationRun)
                    .where(
                        RecommendationRun.cancel_requested.is_(False),
                        (
                            (RecommendationRun.status == "queued")
                            | (
                                (RecommendationRun.status == "running")
                                & (
                                    RecommendationRun.heartbeat_at.is_(None)
                                    | (RecommendationRun.heartbeat_at < stale_before)
                                )
                            )
                        ),
                    )
                    .order_by(RecommendationRun.id.asc())
                )
            )
            .scalars()
            .all()
        )

    async def list_narration_recoverable(self) -> list[RecommendationRun]:
        """Active runs remain readable while unfinished narration is resumed safely."""
        return list(
            (
                await self.session.execute(
                    select(RecommendationRun).where(
                        RecommendationRun.status == "active",
                        (
                            RecommendationRun.request_options_json.like('%"narration_status":"pending"%')
                            | RecommendationRun.request_options_json.like('%"narration_status":"running"%')
                        ),
                    )
                )
            ).scalars().all()
        )

    async def get_active(self, result_id: int) -> RecommendationRun | None:
        return (
            await self.session.execute(
                select(RecommendationRun)
                .where(
                    RecommendationRun.source_result_id == result_id,
                    RecommendationRun.status == "active",
                )
                .order_by(RecommendationRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def list_runs(self, result_id: int) -> list[RecommendationRun]:
        return list(
            (
                await self.session.execute(
                    select(RecommendationRun)
                    .where(RecommendationRun.source_result_id == result_id)
                    .order_by(RecommendationRun.id.desc())
                )
            )
            .scalars()
            .all()
        )

    async def get_latest_attempt(
        self, result_id: int, base_fingerprint: str
    ) -> RecommendationRun | None:
        for run in await self.list_runs(result_id):
            try:
                options = json.loads(run.request_options_json)
            except (TypeError, json.JSONDecodeError):
                continue
            if options.get("base_fingerprint") == base_fingerprint:
                return run
        return None

    async def acquire_narration_lease(
        self, fingerprint: str, claim_token: str, *, stale_after: timedelta
    ) -> tuple[NarrationLeaseAction, RecommendationNarrationLease | None]:
        """Atomically own a packet or reuse its completed wording cache."""
        now = datetime.now(UTC)
        stale_before = now - stale_after
        lease = await self.session.get(RecommendationNarrationLease, fingerprint)
        if lease is None:
            try:
                async with self.session.begin_nested():
                    lease = RecommendationNarrationLease(
                        fingerprint=fingerprint,
                        status="running",
                        claim_token=claim_token,
                        claimed_at=now,
                        updated_at=now,
                    )
                    self.session.add(lease)
                    await self.session.flush()
                return "claimed", lease
            except IntegrityError:
                lease = await self.session.get(RecommendationNarrationLease, fingerprint)
        if lease is None:
            return "busy", None
        if lease.status == "completed" or lease.status.startswith("fallback_"):
            return "cached", lease
        if (
            lease.status == "running"
            and lease.claimed_at
            and _as_utc(lease.claimed_at) >= stale_before
        ):
            return "busy", lease
        lease.status = "running"
        lease.claim_token = claim_token
        lease.claimed_at = now
        lease.updated_at = now
        await self.session.flush()
        return "claimed", lease

    async def finalize_narration_lease(
        self,
        *,
        fingerprint: str,
        claim_token: str,
        status: str,
        polished_reason_json: str | None,
        narration_model: str | None,
        error_code: str | None,
    ) -> bool:
        """Persist a narration outcome only if this worker still owns the lease."""
        result = await self.session.execute(
            update(RecommendationNarrationLease)
            .where(
                RecommendationNarrationLease.fingerprint == fingerprint,
                RecommendationNarrationLease.status == "running",
                RecommendationNarrationLease.claim_token == claim_token,
            )
            .values(
                status=status,
                claim_token=None,
                claimed_at=None,
                polished_reason_json=polished_reason_json,
                narration_model=narration_model,
                error_code=error_code,
                updated_at=datetime.now(UTC),
            )
        )
        return bool(getattr(result, "rowcount", 0))
