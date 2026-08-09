"""add evidence matrix tables

Revision ID: c7d8e9f0a1b2
Revises: b6f9a1c3d7e2
"""

from alembic import op
import sqlalchemy as sa

revision = "c7d8e9f0a1b2"
down_revision = "b6f9a1c3d7e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_matrices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "source_comparison_id",
            sa.Integer(),
            sa.ForeignKey("comparison_tasks.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "matrix_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "matrix_id",
            sa.Integer(),
            sa.ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_notes", sa.Text(), nullable=False),
        sa.Column("topic_relevance", sa.String(length=16), nullable=False),
        sa.Column("reading_status", sa.String(length=16), nullable=False),
        sa.Column("document_status", sa.String(length=16), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("matrix_id", "document_id", name="uq_matrix_documents"),
    )
    op.create_index("ix_matrix_documents_matrix_id", "matrix_documents", ["matrix_id"])
    op.create_table(
        "matrix_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "matrix_id",
            sa.Integer(),
            sa.ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("field_label", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("matrix_id", "field_key", name="uq_matrix_fields"),
    )
    op.create_index("ix_matrix_fields_matrix_id", "matrix_fields", ["matrix_id"])
    op.create_table(
        "matrix_cells",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "matrix_id",
            sa.Integer(),
            sa.ForeignKey("evidence_matrices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("cell_value", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=False),
        sa.Column("generated_value", sa.Text(), nullable=True),
        sa.Column("user_value", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint(
            "matrix_id", "document_id", "field_key", name="uq_matrix_cells"
        ),
    )
    op.create_index("ix_matrix_cells_matrix_id", "matrix_cells", ["matrix_id"])


def downgrade() -> None:
    op.drop_index("ix_matrix_cells_matrix_id", table_name="matrix_cells")
    op.drop_table("matrix_cells")
    op.drop_index("ix_matrix_fields_matrix_id", table_name="matrix_fields")
    op.drop_table("matrix_fields")
    op.drop_index("ix_matrix_documents_matrix_id", table_name="matrix_documents")
    op.drop_table("matrix_documents")
    op.drop_table("evidence_matrices")
