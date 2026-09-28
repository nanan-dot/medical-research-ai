"""persist structured reading-plan reasons and enforce one active plan

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: str | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_reason(reason: str) -> str:
    return json.dumps({
        "headline": "既有阅读计划理由",
        "narrative": reason,
        "stage_fit": [], "research_question_matches": [], "incremental_value": [],
        "evidence_sources": ["既有 recommendation_reason"],
        "limitations": ["该记录在结构化理由迁移前创建，缺少可追溯的输入快照。"],
        "generation_method": "deterministic", "status": "partial",
    }, ensure_ascii=False)


def upgrade() -> None:
    with op.batch_alter_table("reading_plan_items") as batch_op:
        batch_op.add_column(sa.Column("reading_reason_json", sa.Text(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, recommendation_reason FROM reading_plan_items")).fetchall()
    for row in rows:
        bind.execute(sa.text("UPDATE reading_plan_items SET reading_reason_json = :reason WHERE id = :id"), {"id": row.id, "reason": _legacy_reason(row.recommendation_reason)})
    with op.batch_alter_table("reading_plan_items") as batch_op:
        batch_op.alter_column("reading_reason_json", nullable=False)
    active_rows = bind.execute(sa.text(
        "SELECT id, result_id FROM reading_plans WHERE status = 'active' "
        "ORDER BY result_id, COALESCE(activated_at, created_at) DESC, id DESC"
    )).fetchall()
    retained_results: set[int] = set()
    for row in active_rows:
        if row.result_id not in retained_results:
            retained_results.add(row.result_id)
            continue
        bind.execute(
            sa.text("UPDATE reading_plans SET status = 'archived' WHERE id = :id"),
            {"id": row.id},
        )
    op.create_index("uq_reading_plan_one_active", "reading_plans", ["result_id"], unique=True, sqlite_where=sa.text("status = 'active'"), postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("uq_reading_plan_one_active", table_name="reading_plans")
    with op.batch_alter_table("reading_plan_items") as batch_op:
        batch_op.drop_column("reading_reason_json")
