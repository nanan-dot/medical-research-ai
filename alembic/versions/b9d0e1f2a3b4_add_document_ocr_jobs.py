"""add document OCR jobs

Revision ID: b9d0e1f2a3b4
Revises: a8c9d0e1f2a3
Create Date: 2026-08-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b9d0e1f2a3b4"
down_revision: str | None = "a8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_ocr_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("engine_name", sa.String(length=64), nullable=True),
        sa.Column("engine_version", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("completed_pages", sa.Integer(), nullable=False),
        sa.Column("failed_pages", sa.Integer(), nullable=False),
        sa.Column("output_relative_path", sa.String(length=512), nullable=True),
        sa.Column("output_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_ocr_jobs_document_id"), "document_ocr_jobs", ["document_id"])
    op.create_index(op.f("ix_document_ocr_jobs_status"), "document_ocr_jobs", ["status"])
    op.create_table(
        "document_ocr_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("text_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["document_ocr_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_ocr_pages_job_id"), "document_ocr_pages", ["job_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_document_ocr_pages_job_id"), table_name="document_ocr_pages")
    op.drop_table("document_ocr_pages")
    op.drop_index(op.f("ix_document_ocr_jobs_status"), table_name="document_ocr_jobs")
    op.drop_index(op.f("ix_document_ocr_jobs_document_id"), table_name="document_ocr_jobs")
    op.drop_table("document_ocr_jobs")
