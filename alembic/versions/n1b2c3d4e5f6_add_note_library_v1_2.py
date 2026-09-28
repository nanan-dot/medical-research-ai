"""Add note library v1.2 with a frozen schema snapshot.

Revision ID: n1b2c3d4e5f6
Revises: a2c4e6f8b0d1, b7d9f1a3c5e7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = ("a2c4e6f8b0d1", "b7d9f1a3c5e7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create V1.2 tables without importing live ORM metadata."""
    op.create_table(
        "research_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_scope", sa.String(128), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("metadata_version", sa.Integer(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "content_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_research_notes_owner_scope", "research_notes", ["owner_scope"])
    op.create_index(
        "ix_research_notes_content_updated_at", "research_notes", ["content_updated_at"]
    )
    op.create_table(
        "note_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("save_state", sa.String(24), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("note_id", "actor_scope", name="uq_note_draft_actor"),
    )
    op.create_index("ix_note_drafts_note_id", "note_drafts", ["note_id"])
    op.create_table(
        "note_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("restored_from_revision", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("note_id", "revision_no", name="uq_note_revision_no"),
    )
    op.create_index("ix_note_revisions_note_id", "note_revisions", ["note_id"])
    op.create_table(
        "note_source_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("note_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Integer()),
        sa.Column("source_version", sa.String(128)),
        sa.Column("document_id", sa.Integer()),
        sa.Column("anchor_id", sa.Integer()),
        sa.Column("granularity", sa.String(24), nullable=False),
        sa.Column("title_snapshot", sa.String(500), nullable=False),
        sa.Column("quote_snapshot", sa.Text(), nullable=False),
        sa.Column("url_snapshot", sa.Text()),
        sa.Column("created_status", sa.String(24), nullable=False),
    )
    op.create_index(
        "ix_note_source_revision", "note_source_links", ["revision_id", "source_type"]
    )
    op.create_table(
        "note_research_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_context_id",
            sa.Integer(),
            sa.ForeignKey("research_contexts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "note_id", "research_context_id", name="uq_note_research_link"
        ),
    )
    op.create_index(
        "ix_note_research_links_note_id", "note_research_links", ["note_id"]
    )
    op.create_index(
        "ix_note_research_links_research_context_id",
        "note_research_links",
        ["research_context_id"],
    )
    op.create_table(
        "note_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("normalized_name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
    )
    op.create_table(
        "note_tag_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("note_tags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("note_id", "tag_id", name="uq_note_tag_link"),
    )
    op.create_index("ix_note_tag_links_note_id", "note_tag_links", ["note_id"])
    op.create_index("ix_note_tag_links_tag_id", "note_tag_links", ["tag_id"])
    op.create_table(
        "note_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_note_activities_note_id", "note_activities", ["note_id"])
    op.create_table(
        "note_save_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("note_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "actor_scope", "note_id", "idempotency_key", name="uq_note_save_operation"
        ),
    )
    op.create_table(
        "note_ai_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_revision", sa.Integer()),
        sa.Column("input_draft_version", sa.Integer()),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("output_title", sa.String(200)),
        sa.Column("output_body", sa.Text()),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("adopted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_note_ai_suggestions_note_id", "note_ai_suggestions", ["note_id"]
    )
    op.create_table(
        "note_derivations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_scope", sa.String(128), nullable=False),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("note_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.UniqueConstraint(
            "actor_scope", "idempotency_key", name="uq_note_derivation_key"
        ),
    )
    op.create_table(
        "note_legacy_backfills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legacy_id", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("research_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("anchor_id", sa.Integer(), nullable=False),
        sa.Column("quote_snapshot", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    """Remove only the V1.2 note-library structures in dependency order."""
    for table_name in (
        "note_legacy_backfills",
        "note_derivations",
        "note_ai_suggestions",
        "note_save_operations",
        "note_activities",
        "note_tag_links",
        "note_tags",
        "note_research_links",
        "note_source_links",
        "note_revisions",
        "note_drafts",
        "research_notes",
    ):
        op.drop_table(table_name)
