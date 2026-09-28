"""add phase 2 segment metadata for translation jobs

Revision ID: b7d9f1a3c5e7
Revises: f1b3c5d7e9a2
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d9f1a3c5e7"
down_revision: str | None = "f1b3c5d7e9a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("medical_translation_jobs") as batch:
        batch.add_column(sa.Column("layout_segment_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("request_priority", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("request_trigger", sa.String(length=32), nullable=False, server_default="selection"))
        batch.create_foreign_key("fk_translation_job_layout_segment", "document_layout_segments", ["layout_segment_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_translation_job_segment_state", "medical_translation_jobs", ["layout_segment_id", "state"])
    op.create_index(
        "ix_medical_translation_jobs_layout_segment_id",
        "medical_translation_jobs",
        ["layout_segment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medical_translation_jobs_layout_segment_id",
        table_name="medical_translation_jobs",
    )
    op.drop_index("ix_translation_job_segment_state", table_name="medical_translation_jobs")
    with op.batch_alter_table("medical_translation_jobs") as batch:
        batch.drop_constraint("fk_translation_job_layout_segment", type_="foreignkey")
        batch.drop_column("request_trigger")
        batch.drop_column("request_priority")
        batch.drop_column("layout_segment_id")
