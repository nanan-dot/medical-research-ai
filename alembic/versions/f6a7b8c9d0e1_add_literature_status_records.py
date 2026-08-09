"""add literature status records"""
import sqlalchemy as sa

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("literature_status_records", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("status_type", sa.String(32), nullable=False), sa.Column("source", sa.String(64), nullable=False), sa.Column("notice_url_or_id", sa.Text()), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_literature_status_records_document_id", "literature_status_records", ["document_id"])
def downgrade() -> None:
    op.drop_index("ix_literature_status_records_document_id", table_name="literature_status_records")
    op.drop_table("literature_status_records")
