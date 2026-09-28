"""Lease-fenced translation worker; provider calls occur outside DB transactions."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.medical_translation.cache_key import CacheIdentity, cache_key
from app.modules.medical_translation.constants import (
    CONFIG_VERSION,
    LEASE_SECONDS,
    MAX_ATTEMPTS,
    POLICY_VERSION,
    PROMPT_VERSION,
    TASK_TYPE,
    TERMINOLOGY_VERSION,
    VALIDATOR_VERSION,
)
from app.modules.medical_translation.model import (
    MedicalTranslationJob,
    TranslationRevision,
    TranslationTermOverride,
    TranslationValidationReport,
)
from app.modules.medical_translation.provider import (
    ConfiguredTranslationProvider,
    LocalMarianTranslationProvider,
    OllamaMedicalTranslationProvider,
    TranslationProvider,
    TranslationProviderResult,
    local_translation_artifact_ready,
)
from app.modules.medical_translation.quality import (
    QualityReport,
    validate_translation,
)
from app.modules.medical_translation.terminology_dataset import (
    MedicalTerminologyDataset,
)
from app.modules.task.model import TaskRecord
from app.modules.task.repository import TaskRepository

ProviderFactory = Callable[[AsyncSession], Awaitable[TranslationProvider]]


class CacheIdentityBase(TypedDict):
    access_scope: str
    document_id: int
    file_hash: str
    anchor_revision_id: int
    segmentation_revision_id: int
    source_anchor_id: int
    source_text_hash: str
    source_language: str
    target_language: str
    context_hash: str
    terminology_version: str
    prompt_version: str
    config_version: str
    policy_version: str
    validator_version: str


async def _configured(session: AsyncSession) -> TranslationProvider:
    if settings.MEDICAL_TRANSLATION_ENGINE == "ollama":
        if not settings.OLLAMA_MODEL:
            raise RuntimeError("OLLAMA_MODEL is not configured")
        return OllamaMedicalTranslationProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
            terminology_dataset=(
                MedicalTerminologyDataset(settings.MEDICAL_TERMINOLOGY_INDEX_PATH)
                if settings.MEDICAL_TERMINOLOGY_INDEX_PATH is not None
                else None
            ),
        )
    local_directory = settings.MEDICAL_TRANSLATION_LOCAL_MODEL_DIR
    if settings.MEDICAL_TRANSLATION_ENGINE in {"auto", "local-transformers"} and local_translation_artifact_ready(
        local_directory, settings.MEDICAL_TRANSLATION_LOCAL_TOKENIZER_DIR
    ):
        assert local_directory is not None
        return LocalMarianTranslationProvider(
            local_directory,
            settings.MEDICAL_TRANSLATION_LOCAL_DEVICE,
            settings.MEDICAL_TRANSLATION_LOCAL_TOKENIZER_DIR,
            settings.MEDICAL_TRANSLATION_LOCAL_CPU_THREADS,
        )
    return await ConfiguredTranslationProvider.from_session(session)


class MedicalTranslationWorker:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        provider_factory: ProviderFactory = _configured,
    ) -> None:
        self._factory = session_factory
        self._provider_factory = provider_factory
        self._owner = f"translation-{uuid4().hex}"

    async def run_once(self) -> bool:
        task_id: int | None = None
        job_id: int | None = None
        attempts = 0
        try:
            async with self._factory() as session:
                task = await self._claim_next_priority(session)
                if task is None:
                    return False
                detail = json.loads(task.detail_json)
                job_id = detail.get("translation_job_id")
                task_id = task.id
                attempts = task.retry_count
                if not isinstance(job_id, int):
                    await self._fail(
                        session, task, None, "translation_task_invalid", False
                    )
                    await session.commit()
                    return True
                job = await session.get(MedicalTranslationJob, job_id)
                if job is None:
                    await self._fail(
                        session, task, None, "translation_source_missing", False
                    )
                    await session.commit()
                    return True
                if job.state == "cancelled":
                    await session.commit()
                    return True
                job.state = "running"
                job.attempt_count = attempts
                job.started_at = job.started_at or datetime.now(UTC)
                task.phase = "translating"
                anchor = await session.get(DocumentSourceAnchor, job.source_anchor_id)
                revision = await session.get(
                    DocumentAnchorRevision, job.anchor_revision_id
                )
                if anchor is None or revision is None:
                    await self._fail(
                        session, task, job, "translation_source_missing", False
                    )
                    await session.commit()
                    return True
                overrides = list(
                    (
                        await session.scalars(
                            select(TranslationTermOverride).where(
                                TranslationTermOverride.document_id == job.document_id,
                                TranslationTermOverride.target_language
                                == job.target_language,
                            )
                        )
                    ).all()
                )
                glossary = {
                    override.normalized_source_term: override.target_term
                    for override in overrides
                }
                glossary_version = hashlib.sha256(
                    json.dumps(
                        {
                            "base": TERMINOLOGY_VERSION,
                            "entries": sorted(glossary.items()),
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                source_text = anchor.quote
                source_language, target_language = (
                    job.source_language,
                    job.target_language,
                )
                identity_base: CacheIdentityBase = {
                    "access_scope": job.access_scope,
                    "document_id": job.document_id,
                    "file_hash": revision.file_hash,
                    "anchor_revision_id": job.anchor_revision_id,
                    "segmentation_revision_id": job.segmentation_revision_id,
                    "source_anchor_id": job.source_anchor_id,
                    "source_text_hash": job.source_text_hash,
                    "source_language": source_language,
                    "target_language": target_language,
                    "context_hash": hashlib.sha256(b"").hexdigest(),
                    "terminology_version": glossary_version,
                    "prompt_version": PROMPT_VERSION,
                    "config_version": CONFIG_VERSION,
                    "policy_version": POLICY_VERSION,
                    "validator_version": VALIDATOR_VERSION,
                }
                # 将 claim 和 running 状态先提交；配置/提供商失败不能回滚计数，
                # 否则一个无法使用的模型会永久占据 queued 状态。
                await session.commit()
                provider = await self._provider_factory(session)
            result = await self._translate_owned(
                task_id,
                provider,
                source_text,
                source_language,
                target_language,
                glossary,
            )
            await self._publish(
                task_id, job_id, source_text, result, identity_base, glossary
            )
        except Exception as exc:
            if task_id is None or job_id is None:
                raise
            async with self._factory() as session:
                task = await session.get(TaskRecord, task_id)
                job = await session.get(MedicalTranslationJob, job_id)
                if task is not None and task.status not in {"cancelled", "succeeded"}:
                    await self._fail(
                        session,
                        task,
                        job,
                        getattr(exc, "code", "translation_provider_failed"),
                        attempts < MAX_ATTEMPTS,
                    )
                    await session.commit()
        return True

    async def _translate_owned(
        self,
        task_id: int,
        provider: TranslationProvider,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str],
    ) -> TranslationProviderResult:
        work = asyncio.create_task(
            provider.translate(
                source_text=source_text,
                source_language=source_language,
                target_language=target_language,
                glossary=glossary,
            )
        )
        heartbeat = asyncio.create_task(self._heartbeat(task_id))
        try:
            done, _ = await asyncio.wait(
                {work, heartbeat},
                timeout=settings.MEDICAL_TRANSLATION_TIMEOUT_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if work in done:
                return await work
            if heartbeat in done:
                await heartbeat
                raise RuntimeError("translation_lease_lost")
            raise TimeoutError("translation_timeout")
        finally:
            work.cancel()
            heartbeat.cancel()
            await asyncio.gather(work, heartbeat, return_exceptions=True)

    async def _heartbeat(self, task_id: int) -> None:
        while True:
            await asyncio.sleep(10)
            async with self._factory() as session:
                owned = await TaskRepository(session).renew_lease(
                    task_id, self._owner, LEASE_SECONDS
                )
                await session.commit()
            if not owned:
                return

    async def _claim_next_priority(self, session: AsyncSession) -> TaskRecord | None:
        """Claim one lease-fenced job, preferring active reading over speculative work."""
        from datetime import timedelta

        now = datetime.now(UTC)
        available = or_(
            TaskRecord.status == "queued",
            and_(TaskRecord.status == "running", TaskRecord.lease_expires_at < now),
        )
        candidate = await session.scalar(
            select(TaskRecord.id)
            .join(MedicalTranslationJob, MedicalTranslationJob.task_id == TaskRecord.id)
            .where(TaskRecord.task_type == TASK_TYPE, available)
            .order_by(
                MedicalTranslationJob.request_priority.desc(),
                TaskRecord.created_at,
                TaskRecord.id,
            )
            .limit(1)
        )
        if candidate is None:
            return None
        claimed = await session.execute(
            update(TaskRecord)
            .where(TaskRecord.id == candidate, available)
            .values(
                status="running",
                lease_owner=self._owner,
                lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                heartbeat_at=now,
                started_at=func.coalesce(TaskRecord.started_at, now),
                retry_count=TaskRecord.retry_count + 1,
            )
        )
        if getattr(claimed, "rowcount", 0) != 1:
            return None
        return await TaskRepository(session).get(int(candidate))

    async def _publish(
        self,
        task_id: int,
        job_id: int,
        source_text: str,
        result: TranslationProviderResult,
        identity_base: CacheIdentityBase,
        glossary: dict[str, str],
    ) -> None:
        report = validate_translation(source_text, result.translated_text)
        identity = CacheIdentity(
            **identity_base,
            provider=result.provider,
            model=result.model,
            model_revision=result.model_revision,
        )
        if glossary:
            report = replace(
                report,
                terms=tuple(
                    replace(
                        term,
                        target_term=glossary[term.source_term.casefold()],
                        status="user_override",
                        provenance="document-user-override",
                        version=identity.terminology_version,
                    )
                    if term.source_term.casefold() in glossary
                    else term
                    for term in report.terms
                ),
            )
        key = cache_key(identity)
        async with self._factory() as session:
            task = await session.get(TaskRecord, task_id)
            job = await session.get(MedicalTranslationJob, job_id)
            if task is None or job is None or not self._owned(task) or job.state == "cancelled":
                return
            job.state = "quality_checking"
            task.phase = "quality_checking"
            await session.flush()
            cached = await session.scalar(
                select(TranslationRevision).where(
                    TranslationRevision.cache_key == key,
                    TranslationRevision.quality_status != "blocked",
                )
            )
            if cached is None:
                revision = TranslationRevision(
                    job_id=job.id,
                    document_id=job.document_id,
                    source_anchor_id=job.source_anchor_id,
                    anchor_revision_id=job.anchor_revision_id,
                    segmentation_revision_id=job.segmentation_revision_id,
                    version=1,
                    origin="machine",
                    source_text_hash=job.source_text_hash,
                    source_language=job.source_language,
                    target_language=job.target_language,
                    translated_text=result.translated_text,
                    alignment_json=json.dumps(
                        [item.model_dump() for item in result.alignment]
                    ),
                    terminology_json=json.dumps(
                        [asdict(term) for term in report.terms], ensure_ascii=False
                    ),
                    quality_status=report.quality_status,
                    provider=result.provider,
                    model=result.model,
                    model_revision=result.model_revision,
                    terminology_version=identity.terminology_version,
                    cache_key=key,
                )
                session.add(revision)
                await session.flush()
                revision.root_revision_id = revision.id
                session.add(
                    TranslationValidationReport(
                        revision_id=revision.id,
                        validator_version=VALIDATOR_VERSION,
                        issues_json=json.dumps(
                            [asdict(issue) for issue in report.issues],
                            ensure_ascii=False,
                        ),
                        deterministic_passed=0 if report.blocked else 1,
                        highest_severity=_highest(report),
                    )
                )
            else:
                revision = cached
            if task is None or not self._owned(task) or job.state == "cancelled":
                await session.rollback()
                return
            now = datetime.now(UTC)
            job.state = "succeeded"
            job.result_revision_id = revision.id
            job.finished_at = now
            task.status = "succeeded"
            task.phase = "completed"
            task.progress = 100
            task.completed_units = 1
            task.active_idempotency_key = None
            task.lease_owner = None
            task.lease_expires_at = None
            task.finished_at = now
            await session.commit()

    def _owned(self, task: TaskRecord | None) -> bool:
        return bool(
            task and task.status == "running" and task.lease_owner == self._owner
        )

    async def _fail(
        self,
        session: AsyncSession,
        task: TaskRecord,
        job: MedicalTranslationJob | None,
        code: str,
        retry: bool,
    ) -> None:
        now = datetime.now(UTC)
        task.status = "queued" if retry else "failed"
        task.phase = "retry_wait" if retry else "failed"
        task.error_code = code
        task.error_message = "Medical translation did not complete"
        task.lease_owner = None
        task.lease_expires_at = None
        task.finished_at = None if retry else now
        if not retry:
            task.active_idempotency_key = None
        if job is not None and job.state != "cancelled":
            job.state = "queued" if retry else "failed"
            job.error_code = code
            job.error_message = "Medical translation did not complete"
            job.finished_at = None if retry else now


def _highest(report: QualityReport) -> str | None:
    issues = report.issues
    order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    values = [issue.severity for issue in issues]
    return max(values, key=order.__getitem__) if values else None
