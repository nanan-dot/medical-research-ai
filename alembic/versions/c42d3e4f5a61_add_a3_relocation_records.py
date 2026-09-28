"""Add A3 file-version, relocation and backfill audit records.

Revision ID: c42d3e4f5a61
Revises: b31a2c4d5e60
"""

import sqlalchemy as sa

from alembic import op

revision = "c42d3e4f5a61"
down_revision = "b31a2c4d5e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("document_file_revisions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("file_hash", sa.String(64), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("modified_time_ns", sa.Integer()), sa.Column("storage_kind", sa.String(32), nullable=False), sa.Column("storage_reference", sa.Text()), sa.Column("is_current", sa.Boolean(), nullable=False), sa.Column("is_content_available", sa.Boolean(), nullable=False), sa.Column("retention_status", sa.String(32), nullable=False), sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("superseded_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("document_id", "file_hash", name="uq_document_file_revision_hash"))
    op.create_index("uq_document_file_revision_current", "document_file_revisions", ["document_id"], unique=True, sqlite_where=sa.text("is_current = 1"), postgresql_where=sa.text("is_current = true"))
    op.create_table("document_anchor_relocations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="CASCADE"), nullable=False), sa.Column("target_anchor_revision_id", sa.Integer(), sa.ForeignKey("document_anchor_revisions.id", ondelete="CASCADE"), nullable=False), sa.Column("candidate_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="SET NULL")), sa.Column("method", sa.String(32), nullable=False), sa.Column("algorithm_version", sa.String(64), nullable=False), sa.Column("score_breakdown_json", sa.Text(), nullable=False), sa.Column("protected_token_status", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("decision_source", sa.String(32)), sa.Column("reviewer_id", sa.String(128)), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("decision_note", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("source_anchor_id", "target_anchor_revision_id", "candidate_anchor_id", "algorithm_version", name="uq_anchor_relocation_candidate"))
    op.create_index("uq_anchor_relocation_confirmed", "document_anchor_relocations", ["source_anchor_id", "target_anchor_revision_id"], unique=True, sqlite_where=sa.text("status = 'confirmed'"), postgresql_where=sa.text("status = 'confirmed'"))
    op.create_table("asset_anchor_links", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("asset_type", sa.String(64), nullable=False), sa.Column("asset_id", sa.Integer(), nullable=False), sa.Column("original_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), nullable=False), sa.Column("resolved_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="SET NULL")), sa.Column("resolution_status", sa.String(32), nullable=False), sa.Column("resolution_version", sa.Integer(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("asset_type", "asset_id", name="uq_asset_anchor_link"))
    op.create_table("document_anchor_relocation_decisions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("relocation_id", sa.Integer(), sa.ForeignKey("document_anchor_relocations.id", ondelete="CASCADE"), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("decision_source", sa.String(32), nullable=False), sa.Column("reviewer_id", sa.String(128), nullable=False), sa.Column("decision_note", sa.Text()), sa.Column("previous_resolution_version", sa.Integer(), nullable=False), sa.Column("resulting_resolution_version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_document_anchor_relocation_decisions_relocation_id", "document_anchor_relocation_decisions", ["relocation_id"])
    op.create_table("legacy_anchor_backfill_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("task_id", sa.Integer(), sa.ForeignKey("task_records.id", ondelete="SET NULL")), sa.Column("asset_type", sa.String(64), nullable=False), sa.Column("source_schema_version", sa.String(64), nullable=False), sa.Column("target_anchor_revision_id", sa.Integer(), sa.ForeignKey("document_anchor_revisions.id", ondelete="SET NULL")), sa.Column("mode", sa.String(16), nullable=False), sa.Column("cursor", sa.String(128)), sa.Column("total", sa.Integer(), nullable=False), sa.Column("scanned", sa.Integer(), nullable=False), sa.Column("exact", sa.Integer(), nullable=False), sa.Column("candidate", sa.Integer(), nullable=False), sa.Column("unresolved", sa.Integer(), nullable=False), sa.Column("failed", sa.Integer(), nullable=False), sa.Column("algorithm_version", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("report_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True)))
    op.create_table("legacy_anchor_backfill_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_id", sa.Integer(), sa.ForeignKey("legacy_anchor_backfill_runs.id", ondelete="CASCADE"), nullable=False), sa.Column("asset_type", sa.String(64), nullable=False), sa.Column("asset_id", sa.Integer(), nullable=False), sa.Column("legacy_identity_hash", sa.String(64), nullable=False), sa.Column("result_status", sa.String(32), nullable=False), sa.Column("anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="SET NULL")), sa.Column("candidate_count", sa.Integer(), nullable=False), sa.Column("reason_codes_json", sa.Text(), nullable=False), sa.Column("error_code", sa.String(64)), sa.UniqueConstraint("run_id", "asset_type", "asset_id", name="uq_anchor_backfill_item"))
    for table, column in [("document_file_revisions", "document_id"), ("document_anchor_relocations", "source_anchor_id"), ("document_anchor_relocations", "target_anchor_revision_id"), ("asset_anchor_links", "original_anchor_id"), ("asset_anchor_links", "resolved_anchor_id"), ("legacy_anchor_backfill_runs", "task_id"), ("legacy_anchor_backfill_items", "run_id")]: op.create_index(f"ix_{table}_{column}", table, [column])
    with op.batch_alter_table("document_anchor_revisions") as batch:
        batch.add_column(sa.Column("document_file_revision_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_anchor_file_revision", "document_file_revisions", ["document_file_revision_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_document_anchor_revisions_document_file_revision_id", ["document_file_revision_id"])
    with op.batch_alter_table("citations") as batch:
        batch.add_column(sa.Column("source_anchor_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("anchor_status", sa.String(32), nullable=False, server_default="legacy_unversioned"))
        batch.create_foreign_key("fk_citation_source_anchor", "document_source_anchors", ["source_anchor_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_citations_source_anchor_id", ["source_anchor_id"])


def downgrade() -> None:
    connection = op.get_bind()
    relocated_assets = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM asset_anchor_links "
            "WHERE resolved_anchor_id IS NOT NULL "
            "AND resolved_anchor_id != original_anchor_id"
        )
    ).scalar_one()
    if relocated_assets:
        raise RuntimeError("DOWNGRADE_WOULD_LOSE_NEW_ASSETS")
    with op.batch_alter_table("citations") as batch:
        batch.drop_index("ix_citations_source_anchor_id")
        batch.drop_constraint("fk_citation_source_anchor", type_="foreignkey")
        batch.drop_column("anchor_status")
        batch.drop_column("source_anchor_id")
    with op.batch_alter_table("document_anchor_revisions") as batch:
        batch.drop_index("ix_document_anchor_revisions_document_file_revision_id")
        batch.drop_constraint("fk_anchor_file_revision", type_="foreignkey")
        batch.drop_column("document_file_revision_id")
    for table in ["legacy_anchor_backfill_items", "legacy_anchor_backfill_runs", "document_anchor_relocation_decisions", "asset_anchor_links", "document_anchor_relocations", "document_file_revisions"]: op.drop_table(table)
