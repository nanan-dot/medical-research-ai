"""Immutable translation artifacts and asynchronous job metadata."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.medical_translation.constants import (
    CONFIG_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    TERMINOLOGY_VERSION,
    VALIDATOR_VERSION,
)


class MedicalTranslationJob(Base):
    __tablename__ = "medical_translation_jobs"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "idempotency_key", name="uq_translation_job_idempotency"
        ),
        Index("ix_translation_job_segment_state", "layout_segment_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task_records.id", ondelete="CASCADE"), unique=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True
    )
    layout_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_layout_segments.id", ondelete="SET NULL"), index=True
    )
    request_priority: Mapped[int] = mapped_column(Integer, default=0)
    request_trigger: Mapped[str] = mapped_column(String(32), default="selection")
    anchor_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="RESTRICT")
    )
    segmentation_revision_id: Mapped[int] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="RESTRICT")
    )
    source_text_hash: Mapped[str] = mapped_column(String(64))
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    access_scope: Mapped[str] = mapped_column(String(64), default="local")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    result_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "translation_revisions.id", use_alter=True, name="fk_translation_job_result"
        )
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(300))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TranslationRevision(Base):
    __tablename__ = "translation_revisions"
    __table_args__ = (
        UniqueConstraint(
            "root_revision_id", "version", name="uq_translation_revision_version"
        ),
        UniqueConstraint("cache_key", name="uq_translation_revision_cache_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("medical_translation_jobs.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_anchor_id: Mapped[int] = mapped_column(
        ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), index=True
    )
    anchor_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_anchor_revisions.id", ondelete="RESTRICT")
    )
    segmentation_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_segmentation_revisions.id", ondelete="RESTRICT")
    )
    root_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("translation_revisions.id", ondelete="RESTRICT"), index=True
    )
    supersedes_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("translation_revisions.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    origin: Mapped[str] = mapped_column(String(16), default="machine")
    source_text_hash: Mapped[str] = mapped_column(String(64))
    source_language: Mapped[str] = mapped_column(String(16), default="en")
    target_language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    translated_text: Mapped[str] = mapped_column(Text)
    alignment_json: Mapped[str] = mapped_column(Text, default="[]")
    terminology_json: Mapped[str] = mapped_column(Text, default="[]")
    quality_status: Mapped[str] = mapped_column(String(32), default="needs_review")
    provider: Mapped[str] = mapped_column(String(64), default="manual")
    model: Mapped[str] = mapped_column(String(128), default="human")
    model_revision: Mapped[str] = mapped_column(String(64), default="unknown")
    prompt_version: Mapped[str] = mapped_column(String(64), default=PROMPT_VERSION)
    config_version: Mapped[str] = mapped_column(String(64), default=CONFIG_VERSION)
    policy_version: Mapped[str] = mapped_column(String(64), default=POLICY_VERSION)
    terminology_version: Mapped[str] = mapped_column(
        String(64), default=TERMINOLOGY_VERSION
    )
    validator_version: Mapped[str] = mapped_column(
        String(64), default=VALIDATOR_VERSION
    )
    context_hash: Mapped[str] = mapped_column(
        String(64), default=lambda: hashlib.sha256(b"").hexdigest()
    )
    cache_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    @classmethod
    def synthetic_for_test(
        cls,
        *,
        document_id: int,
        source_anchor_id: int,
        source_text_hash: str,
        translated_text: str,
    ) -> TranslationRevision:
        return cls(
            document_id=document_id,
            source_anchor_id=source_anchor_id,
            source_text_hash=source_text_hash,
            translated_text=translated_text,
            origin="machine",
            quality_status="machine_checked",
            version=1,
        )


class TranslationValidationReport(Base):
    __tablename__ = "translation_validation_reports"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("translation_revisions.id", ondelete="CASCADE"), unique=True
    )
    validator_version: Mapped[str] = mapped_column(String(64))
    issues_json: Mapped[str] = mapped_column(Text, default="[]")
    deterministic_passed: Mapped[int] = mapped_column(Integer, default=0)
    highest_severity: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class TranslationReview(Base):
    __tablename__ = "translation_reviews"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_revision_id: Mapped[int] = mapped_column(
        ForeignKey("translation_revisions.id", ondelete="RESTRICT"), index=True
    )
    corrected_revision_id: Mapped[int] = mapped_column(
        ForeignKey("translation_revisions.id", ondelete="RESTRICT"), unique=True
    )
    expected_version: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewer_scope: Mapped[str] = mapped_column(String(64), default="local-user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class TranslationTermOverride(Base):
    """A user-owned document glossary entry; never a global vocabulary mutation."""

    __tablename__ = "translation_term_overrides"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "normalized_source_term",
            "target_language",
            name="uq_translation_term_override_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_term: Mapped[str] = mapped_column(String(256))
    normalized_source_term: Mapped[str] = mapped_column(String(256))
    target_term: Mapped[str] = mapped_column(String(256))
    target_language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    scope: Mapped[str] = mapped_column(String(32), default="document")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
