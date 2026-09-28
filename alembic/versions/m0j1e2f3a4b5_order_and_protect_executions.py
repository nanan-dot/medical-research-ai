"""Order external executions and protect the SQLite recovery audit chain.

Revision ID: m0j1e2f3a4b5
Revises: m0i1d2e3f4a5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m0j1e2f3a4b5"
down_revision: str | Sequence[str] | None = "m0i1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 保留审计引用；即使某连接忘记开启 foreign_keys，也不能删除已引用的身份。
PROTECTED = (
    ("agent_runs", "run_id", "run_id"),
    ("agent_steps", "step_id", "step_id"),
    ("model_transfer_authorizations", "authorization_id", "authorization_id"),
    ("agent_budget_reservations", "reservation_id", "reservation_id"),
    ("agent_idempotency_records", "idempotency_id", "idempotency_record_id"),
    ("agent_artifacts", "artifact_id", "formal_artifact_id"),
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        raise RuntimeError("M0 execution retention migration supports SQLite only")
    op.add_column("agent_external_executions", sa.Column("execution_seq", sa.Integer()))
    # 旧记录以 SQLite 插入 rowid 排序，避免同时间戳时使用随机 UUID。
    op.execute("""
        UPDATE agent_external_executions AS e SET execution_seq = (
            SELECT COUNT(*) FROM agent_external_executions AS p
            WHERE p.run_id = e.run_id AND p.rowid <= e.rowid
        )
    """)
    with op.batch_alter_table("agent_external_executions") as batch:
        batch.alter_column("execution_seq", nullable=False)
        batch.create_unique_constraint("uq_execution_run_seq", ["run_id", "execution_seq"])
        batch.create_check_constraint("ck_execution_seq_positive", "execution_seq >= 1")
    for table, identity, binding in PROTECTED:
        for operation in ("DELETE", f"UPDATE OF {identity}"):
            suffix = "delete" if operation == "DELETE" else "identity"
            op.execute(f"""
                CREATE TRIGGER m0_keep_{table}_{suffix} BEFORE {operation} ON {table}
                WHEN EXISTS (SELECT 1 FROM agent_external_executions
                             WHERE {binding} = OLD.{identity})
                BEGIN SELECT RAISE(ABORT, 'M0 execution audit reference retained'); END
            """)
    op.execute("""
        CREATE TRIGGER m0_keep_execution_delete BEFORE DELETE ON agent_external_executions
        BEGIN SELECT RAISE(ABORT, 'M0 execution ledger retained'); END
    """)
    op.execute("""
        CREATE TRIGGER m0_keep_execution_identity BEFORE UPDATE OF
        execution_id, execution_seq, research_context_id, run_id, step_id, attempt,
        authorization_id, reservation_id, request_fingerprint, input_hash
        ON agent_external_executions
        BEGIN SELECT RAISE(ABORT, 'M0 execution identity immutable'); END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER m0_keep_execution_identity")
    op.execute("DROP TRIGGER m0_keep_execution_delete")
    for table, _, _ in PROTECTED:
        for suffix in ("delete", "identity"):
            op.execute(f"DROP TRIGGER m0_keep_{table}_{suffix}")
    with op.batch_alter_table("agent_external_executions") as batch:
        batch.drop_constraint("uq_execution_run_seq", type_="unique")
        batch.drop_constraint("ck_execution_seq_positive", type_="check")
        batch.drop_column("execution_seq")
