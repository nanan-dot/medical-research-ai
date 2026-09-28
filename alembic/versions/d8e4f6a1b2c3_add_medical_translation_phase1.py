"""add anchored medical translation phase 1

Revision ID: d8e4f6a1b2c3
Revises: c5a7e2d9f1b3
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d8e4f6a1b2c3"
down_revision: str | None = "c5a7e2d9f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medical_translation_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("source_anchor_id", sa.Integer(), nullable=False),
        sa.Column("anchor_revision_id", sa.Integer(), nullable=False),
        sa.Column("segmentation_revision_id", sa.Integer(), nullable=False),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column("source_language", sa.String(length=16), nullable=False),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("access_scope", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result_revision_id", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=300), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["anchor_revision_id"],
            ["document_anchor_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["result_revision_id"],
            ["translation_revisions.id"],
            name="fk_translation_job_result",
        ),
        sa.ForeignKeyConstraint(
            ["segmentation_revision_id"],
            ["document_segmentation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_anchor_id"], ["document_source_anchors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["task_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "idempotency_key", name="uq_translation_job_idempotency"
        ),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(
        op.f("ix_medical_translation_jobs_document_id"),
        "medical_translation_jobs",
        ["document_id"],
    )
    op.create_index(
        op.f("ix_medical_translation_jobs_source_anchor_id"),
        "medical_translation_jobs",
        ["source_anchor_id"],
    )
    op.create_index(
        op.f("ix_medical_translation_jobs_state"), "medical_translation_jobs", ["state"]
    )

    op.create_table(
        "translation_revisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("source_anchor_id", sa.Integer(), nullable=False),
        sa.Column("anchor_revision_id", sa.Integer(), nullable=True),
        sa.Column("segmentation_revision_id", sa.Integer(), nullable=True),
        sa.Column("root_revision_id", sa.Integer(), nullable=True),
        sa.Column("supersedes_revision_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column("source_language", sa.String(length=16), nullable=False),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("alignment_json", sa.Text(), nullable=False),
        sa.Column("terminology_json", sa.Text(), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("model_revision", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("terminology_version", sa.String(length=64), nullable=False),
        sa.Column("validator_version", sa.String(length=64), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["anchor_revision_id"],
            ["document_anchor_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["medical_translation_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["root_revision_id"], ["translation_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["segmentation_revision_id"],
            ["document_segmentation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_anchor_id"], ["document_source_anchors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["translation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key", name="uq_translation_revision_cache_key"),
        sa.UniqueConstraint(
            "root_revision_id", "version", name="uq_translation_revision_version"
        ),
    )
    op.create_index(
        op.f("ix_translation_revisions_document_id"),
        "translation_revisions",
        ["document_id"],
    )
    op.create_index(
        op.f("ix_translation_revisions_job_id"), "translation_revisions", ["job_id"]
    )
    op.create_index(
        op.f("ix_translation_revisions_root_revision_id"),
        "translation_revisions",
        ["root_revision_id"],
    )
    op.create_index(
        op.f("ix_translation_revisions_source_anchor_id"),
        "translation_revisions",
        ["source_anchor_id"],
    )
    op.create_table(
        "translation_validation_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("validator_version", sa.String(length=64), nullable=False),
        sa.Column("issues_json", sa.Text(), nullable=False),
        sa.Column("deterministic_passed", sa.Integer(), nullable=False),
        sa.Column("highest_severity", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["translation_revisions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_table(
        "translation_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_revision_id", sa.Integer(), nullable=False),
        sa.Column("corrected_revision_id", sa.Integer(), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer_scope", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["base_revision_id"], ["translation_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["corrected_revision_id"], ["translation_revisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corrected_revision_id"),
    )
    op.create_index(
        op.f("ix_translation_reviews_base_revision_id"),
        "translation_reviews",
        ["base_revision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_translation_reviews_base_revision_id"),
        table_name="translation_reviews",
    )
    op.drop_table("translation_reviews")
    op.drop_table("translation_validation_reports")
    op.drop_index(
        op.f("ix_translation_revisions_source_anchor_id"),
        table_name="translation_revisions",
    )
    op.drop_index(
        op.f("ix_translation_revisions_root_revision_id"),
        table_name="translation_revisions",
    )
    op.drop_index(
        op.f("ix_translation_revisions_job_id"), table_name="translation_revisions"
    )
    op.drop_index(
        op.f("ix_translation_revisions_document_id"), table_name="translation_revisions"
    )
    op.drop_table("translation_revisions")
    op.drop_index(
        op.f("ix_medical_translation_jobs_state"), table_name="medical_translation_jobs"
    )
    op.drop_index(
        op.f("ix_medical_translation_jobs_source_anchor_id"),
        table_name="medical_translation_jobs",
    )
    op.drop_index(
        op.f("ix_medical_translation_jobs_document_id"),
        table_name="medical_translation_jobs",
    )
    op.drop_table("medical_translation_jobs")
