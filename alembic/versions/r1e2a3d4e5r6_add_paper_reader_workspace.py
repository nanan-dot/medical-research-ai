"""add paper reader workspace

Revision ID: r1e2a3d4e5r6
Revises: p3d4e5f6a7b8
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "r1e2a3d4e5r6"
down_revision: str | None = "p3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("reader_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("document_file_hash", sa.String(64), nullable=False), sa.Column("anchor_revision_id", sa.Integer(), sa.ForeignKey("document_anchor_revisions.id", ondelete="SET NULL")), sa.Column("segmentation_revision_id", sa.Integer(), sa.ForeignKey("document_segmentation_revisions.id", ondelete="SET NULL")), sa.Column("device_id", sa.String(128), nullable=False), sa.Column("idempotency_key", sa.String(128)), sa.Column("idempotency_payload_hash", sa.String(64)), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.Column("last_page", sa.Integer(), nullable=False, server_default="1"), sa.Column("last_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="SET NULL")), sa.Column("viewport_offset_ratio", sa.Float(), nullable=False, server_default="0"), sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"), sa.Column("close_reason", sa.String(32)), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("is_history_hidden", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.CheckConstraint("last_page >= 1", name="ck_reader_session_page"), sa.CheckConstraint("viewport_offset_ratio >= 0 AND viewport_offset_ratio <= 1", name="ck_reader_session_offset"))
    op.create_index("ix_reader_session_history", "reader_sessions", ["actor_scope", "last_seen_at", "id"])
    op.create_index("uq_reader_session_idempotency", "reader_sessions", ["actor_scope", "idempotency_key"], unique=True)
    op.create_table("reader_page_exposures", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("session_id", sa.Integer(), sa.ForeignKey("reader_sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("page_number", sa.Integer(), nullable=False), sa.Column("first_visible_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_visible_at", sa.DateTime(timezone=True), nullable=False), sa.Column("visible_milliseconds", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_visible_ratio", sa.Float(), nullable=False, server_default="0"), sa.Column("qualified_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("session_id", "page_number", name="uq_reader_exposure_page"))
    op.create_table("reader_preferences", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE")), sa.Column("view_mode", sa.String(16), nullable=False, server_default="original"), sa.Column("zoom_percent", sa.Integer(), nullable=False, server_default="100"), sa.Column("left_panel_mode", sa.String(32), nullable=False, server_default="outline"), sa.Column("left_collapsed", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("right_panel_tab", sa.String(32), nullable=False, server_default="copilot"), sa.Column("focus_mode", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("actor_scope", "document_id", name="uq_reader_preference_scope_document"))
    op.create_table("reader_bookmarks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("source_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), nullable=False), sa.Column("label", sa.String(200)), sa.Column("color", sa.String(32)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("reader_questions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("source_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="open"), sa.Column("linked_conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="SET NULL")), sa.Column("linked_message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_reader_question_status"))
    op.create_table("research_material_candidates", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("research_context_id", sa.Integer(), sa.ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("source_anchor_id", sa.Integer(), sa.ForeignKey("document_source_anchors.id", ondelete="RESTRICT"), nullable=False), sa.Column("candidate_type", sa.String(16), nullable=False), sa.Column("title", sa.String(300)), sa.Column("note", sa.Text()), sa.Column("status", sa.String(16), nullable=False, server_default="candidate"), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("idempotency_payload_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("actor_scope", "idempotency_key", name="uq_research_candidate_idempotency"), sa.CheckConstraint("status IN ('candidate','accepted','rejected')", name="ck_research_candidate_status"))
    op.create_table("paper_reader_states", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_table("reader_idempotency_records", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_scope", sa.String(128), nullable=False), sa.Column("action", sa.String(32), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("payload_hash", sa.String(64), nullable=False), sa.Column("resource_id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("actor_scope", "action", "idempotency_key", name="uq_reader_idempotency_action_key"))
    for table, column in (
        ("paper_reader_states", "actor_scope"),
        ("reader_idempotency_records", "actor_scope"),
        ("reader_bookmarks", "actor_scope"), ("reader_bookmarks", "document_id"), ("reader_bookmarks", "source_anchor_id"),
        ("reader_page_exposures", "qualified_at"), ("reader_page_exposures", "session_id"),
        ("reader_preferences", "actor_scope"),
        ("reader_questions", "actor_scope"), ("reader_questions", "document_id"), ("reader_questions", "source_anchor_id"), ("reader_questions", "status"),
        ("reader_sessions", "actor_scope"), ("reader_sessions", "document_id"), ("reader_sessions", "last_seen_at"), ("reader_sessions", "library_item_id"), ("reader_sessions", "status"),
        ("research_material_candidates", "actor_scope"), ("research_material_candidates", "document_id"), ("research_material_candidates", "research_context_id"), ("research_material_candidates", "source_anchor_id"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table, column in (
        ("paper_reader_states", "actor_scope"),
        ("reader_idempotency_records", "actor_scope"),
        ("reader_bookmarks", "actor_scope"), ("reader_bookmarks", "document_id"), ("reader_bookmarks", "source_anchor_id"),
        ("reader_page_exposures", "qualified_at"), ("reader_page_exposures", "session_id"),
        ("reader_preferences", "actor_scope"),
        ("reader_questions", "actor_scope"), ("reader_questions", "document_id"), ("reader_questions", "source_anchor_id"), ("reader_questions", "status"),
        ("reader_sessions", "actor_scope"), ("reader_sessions", "document_id"), ("reader_sessions", "last_seen_at"), ("reader_sessions", "library_item_id"), ("reader_sessions", "status"),
        ("research_material_candidates", "actor_scope"), ("research_material_candidates", "document_id"), ("research_material_candidates", "research_context_id"), ("research_material_candidates", "source_anchor_id"),
    ):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    for table in ("reader_idempotency_records", "paper_reader_states", "research_material_candidates", "reader_questions", "reader_bookmarks", "reader_preferences", "reader_page_exposures"):
        op.drop_table(table)
    op.drop_index("ix_reader_session_history", table_name="reader_sessions")
    op.drop_index("uq_reader_session_idempotency", table_name="reader_sessions")
    op.drop_table("reader_sessions")
