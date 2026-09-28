"""add journal metric imports

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_metric_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("edition_year", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_version", sa.String(100), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("source_file_hash", sa.String(64), nullable=False),
        sa.Column("license_provenance", sa.Text(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ready"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_summary", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "edition_year BETWEEN 1900 AND 2200", name="ck_journal_metric_batch_year"
        ),
        sa.CheckConstraint(
            "record_count >= 0", name="ck_journal_metric_batch_record_count"
        ),
        sa.UniqueConstraint(
            "provider",
            "edition_year",
            "provider_version",
            name="uq_journal_metric_import_provider_year_version",
        ),
    )
    op.create_index(
        "ix_journal_metric_import_batches_edition_year",
        "journal_metric_import_batches",
        ["edition_year"],
    )
    op.create_index(
        "ix_journal_metric_import_batches_source_file_hash",
        "journal_metric_import_batches",
        ["source_file_hash"],
    )
    columns = [
        sa.Column(
            "import_batch_id",
            sa.Integer(),
        ),
        sa.Column("journal_name", sa.String(500)),
        sa.Column("normalized_journal_name", sa.String(500)),
        sa.Column("issn", sa.String(9)),
        sa.Column("eissn", sa.String(9)),
        sa.Column("issn_l", sa.String(9)),
        sa.Column("impact_factor_year", sa.Integer()),
        sa.Column("jcr_best_quartile", sa.String(2)),
        sa.Column("jcr_year", sa.Integer()),
        sa.Column("wos_indexes_json", sa.Text()),
        sa.Column("wos_year", sa.Integer()),
        sa.Column("cas_quartile", sa.String(2)),
        sa.Column("cas_year", sa.Integer()),
        sa.Column("cas_category", sa.String(200)),
        sa.Column("is_cas_top", sa.Boolean()),
        sa.Column("warning_status", sa.String(100)),
    ]
    # SQLite 不能直接 ALTER 外键/唯一约束；batch 模式复制表并完整搬迁既有行。
    with op.batch_alter_table(
        "literature_commercial_journal_metrics", recreate="always"
    ) as batch_op:
        for column in columns:
            batch_op.add_column(column)
        for name in (
            "import_batch_id",
            "normalized_journal_name",
            "issn",
            "eissn",
            "issn_l",
        ):
            batch_op.create_index(
                f"ix_literature_commercial_journal_metrics_{name}", [name]
            )
        batch_op.create_unique_constraint(
            "uq_journal_metric_batch_key", ["import_batch_id", "journal_key"]
        )
        batch_op.create_foreign_key(
            "fk_journal_metric_import_batch",
            "journal_metric_import_batches",
            ["import_batch_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "literature_commercial_journal_metrics", recreate="always"
    ) as batch_op:
        batch_op.drop_constraint("uq_journal_metric_batch_key", type_="unique")
        batch_op.drop_constraint("fk_journal_metric_import_batch", type_="foreignkey")
        for name in reversed(
            ("import_batch_id", "normalized_journal_name", "issn", "eissn", "issn_l")
        ):
            batch_op.drop_index(f"ix_literature_commercial_journal_metrics_{name}")
        for name in reversed(
            (
                "import_batch_id",
                "journal_name",
                "normalized_journal_name",
                "issn",
                "eissn",
                "issn_l",
                "impact_factor_year",
                "jcr_best_quartile",
                "jcr_year",
                "wos_indexes_json",
                "wos_year",
                "cas_quartile",
                "cas_year",
                "cas_category",
                "is_cas_top",
                "warning_status",
            )
        ):
            batch_op.drop_column(name)
    op.drop_index(
        "ix_journal_metric_import_batches_source_file_hash",
        table_name="journal_metric_import_batches",
    )
    op.drop_index(
        "ix_journal_metric_import_batches_edition_year",
        table_name="journal_metric_import_batches",
    )
    op.drop_table("journal_metric_import_batches")
