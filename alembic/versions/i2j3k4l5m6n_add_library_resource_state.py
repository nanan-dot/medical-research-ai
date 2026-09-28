"""add library resource state

Revision ID: i2j3k4l5m6n
Revises: h1i2j3k4l5m6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i2j3k4l5m6n"
down_revision: str | None = "h1i2j3k4l5m6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("zotero_item_key", sa.String(length=32)))
        batch.add_column(sa.Column("zotero_parent_item_key", sa.String(length=32)))
        batch.add_column(sa.Column("zotero_version", sa.String(length=64)))
        batch.add_column(sa.Column("metadata_only", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_unique_constraint("uq_documents_source_zotero_item", ["knowledge_source_id", "zotero_item_key"])
        batch.create_index("ix_documents_source_modified_time", ["knowledge_source_id", "modified_time"])
    op.create_table("document_accesses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_opened_by", sa.String(length=128)), sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("last_open_request_key", sa.String(length=128)))
    op.create_index("ix_document_accesses_last_opened", "document_accesses", ["last_opened_at", "document_id"])
    op.create_table("zotero_libraries", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("knowledge_source_id", sa.Integer(), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("library_type", sa.String(length=16), nullable=False), sa.Column("library_id", sa.String(length=64), nullable=False), sa.Column("version_cursor", sa.String(length=64)), sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("last_error_code", sa.String(length=64)), sa.Column("last_synced_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("library_type", "library_id", name="uq_zotero_library_identity"))
    op.create_table("zotero_collections", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("zotero_library_id", sa.Integer(), sa.ForeignKey("zotero_libraries.id", ondelete="CASCADE"), nullable=False), sa.Column("collection_key", sa.String(length=32), nullable=False), sa.Column("parent_key", sa.String(length=32)), sa.Column("name", sa.String(length=255), nullable=False), sa.Column("version", sa.String(length=64)), sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.UniqueConstraint("zotero_library_id", "collection_key", name="uq_zotero_collection_key"))
    op.create_index("ix_zotero_collections_parent", "zotero_collections", ["zotero_library_id", "parent_key"])


def downgrade() -> None:
    op.drop_index("ix_zotero_collections_parent", table_name="zotero_collections")
    op.drop_table("zotero_collections")
    op.drop_table("zotero_libraries")
    op.drop_index("ix_document_accesses_last_opened", table_name="document_accesses")
    op.drop_table("document_accesses")
    with op.batch_alter_table("documents") as batch:
        batch.drop_index("ix_documents_source_modified_time")
        batch.drop_constraint("uq_documents_source_zotero_item", type_="unique")
        batch.drop_column("metadata_only")
        batch.drop_column("zotero_version")
        batch.drop_column("zotero_parent_item_key")
        batch.drop_column("zotero_item_key")
