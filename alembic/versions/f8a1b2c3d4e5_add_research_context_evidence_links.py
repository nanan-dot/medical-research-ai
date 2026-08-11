"""Add research contexts and verified writing-evidence links.

Revision ID: f8a1b2c3d4e5
Revises: c0e1f2a3b4c5
"""

import sqlalchemy as sa

from alembic import op

revision = "f8a1b2c3d4e5"
down_revision = "c0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "research_context_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_context_id", sa.Integer(), sa.ForeignKey("research_contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("research_context_id", "document_id", name="uq_research_context_document"),
    )
    op.create_index("ix_research_context_documents_research_context_id", "research_context_documents", ["research_context_id"])
    op.create_index("ix_research_context_documents_document_id", "research_context_documents", ["document_id"])

    for table_name in ("conversations", "evidence_matrices", "writing_projects", "literature_search_tasks"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("research_context_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table_name}_research_context", "research_contexts",
                ["research_context_id"], ["id"], ondelete="SET NULL",
            )
            batch_op.create_index(f"ix_{table_name}_research_context_id", ["research_context_id"])

    with op.batch_alter_table("writing_versions") as batch_op:
        batch_op.add_column(sa.Column("evidence_references_json", sa.Text(), nullable=False, server_default="[]"))

    op.create_table(
        "writing_evidence_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("writing_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("segment_id", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_citation_id", sa.Integer(), sa.ForeignKey("citations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("matrix_cell_id", sa.Integer(), sa.ForeignKey("matrix_cells.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=300), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("citation_text", sa.Text(), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("doi", sa.String(length=300), nullable=True),
        sa.Column("locator", sa.String(length=300), nullable=True),
    )
    op.create_index("ix_writing_evidence_references_project_id", "writing_evidence_references", ["project_id"])
    op.create_index("ix_writing_evidence_references_segment_id", "writing_evidence_references", ["segment_id"])
    op.create_index("ix_writing_evidence_references_document_id", "writing_evidence_references", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_writing_evidence_references_document_id", table_name="writing_evidence_references")
    op.drop_index("ix_writing_evidence_references_segment_id", table_name="writing_evidence_references")
    op.drop_index("ix_writing_evidence_references_project_id", table_name="writing_evidence_references")
    op.drop_table("writing_evidence_references")
    with op.batch_alter_table("writing_versions") as batch_op:
        batch_op.drop_column("evidence_references_json")
    for table_name in ("literature_search_tasks", "writing_projects", "evidence_matrices", "conversations"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_research_context_id")
            batch_op.drop_constraint(f"fk_{table_name}_research_context", type_="foreignkey")
            batch_op.drop_column("research_context_id")
    op.drop_index("ix_research_context_documents_document_id", table_name="research_context_documents")
    op.drop_index("ix_research_context_documents_research_context_id", table_name="research_context_documents")
    op.drop_table("research_context_documents")
    op.drop_table("research_contexts")
