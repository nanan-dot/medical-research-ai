"""Executable migration gates for fresh and pre-fix M0 databases."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]


def run_alembic(database: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=REPO,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def assert_m0i_schema(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(agent_root_budgets)")
        }
        execution_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_external_executions'"
        ).fetchone()
        execution_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(agent_external_executions)")
        }
        retention_triggers = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'm0_keep_%'"
            )
        }
    assert revision == ("m0j1e2f3a4b5",)
    assert {
        "max_model_http_attempts",
        "max_other_http_attempts",
        "reserved_active_seconds",
        "settled_active_seconds",
    } <= columns
    assert execution_table == ("agent_external_executions",)
    assert "execution_seq" in execution_columns
    assert {
        "m0_keep_execution_delete",
        "m0_keep_execution_identity",
        "m0_keep_agent_runs_delete",
        "m0_keep_agent_steps_delete",
        "m0_keep_model_transfer_authorizations_delete",
        "m0_keep_agent_budget_reservations_delete",
        "m0_keep_agent_idempotency_records_delete",
        "m0_keep_agent_artifacts_delete",
    } <= retention_triggers


def test_fresh_database_upgrades_to_single_m0_head(tmp_path: Path) -> None:
    database = tmp_path / "fresh.db"
    run_alembic(database, "upgrade", "head")
    assert_m0i_schema(database)


def test_existing_m0f_database_upgrades_without_runtime_ddl(tmp_path: Path) -> None:
    database = tmp_path / "existing.db"
    run_alembic(database, "upgrade", "m0f1a2b3c4d5")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO agent_root_budgets "
            "(budget_id, root_run_id, max_model_attempts, max_input_tokens, "
            "max_output_tokens, max_retrieval_http, max_total_http, max_tool_calls, "
            "max_active_seconds, reserved_retrieval_http, reserved_total_http, "
            "settled_retrieval_http, settled_total_http) "
            "VALUES ('budget-existing', 'root-existing', 5, 100, 100, 3, 10, 3, "
            "60, 1, 3, 1, 4)"
        )
        connection.execute(
            "INSERT INTO agent_budget_reservations "
            "(reservation_id, budget_id, child_run_id, step_id, attempt, provider, "
            "reserved_retrieval_http, actual_retrieval_http, reserved_total_http, "
            "actual_total_http, status, request_fingerprint, created_at) "
            "VALUES ('reservation-existing', 'budget-existing', 'child-existing', "
            "'step-existing', 1, 'provider', 1, 1, 3, 2, 'settled', "
            "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', "
            "'2026-09-15 00:00:00')"
        )
        connection.commit()
    run_alembic(database, "upgrade", "head")
    assert_m0i_schema(database)
    with sqlite3.connect(database) as connection:
        budget = connection.execute(
            "SELECT max_model_http_attempts, reserved_model_http_attempts, "
            "settled_model_http_attempts FROM agent_root_budgets "
            "WHERE budget_id = 'budget-existing'"
        ).fetchone()
        reservation = connection.execute(
            "SELECT reserved_model_http_attempts, actual_model_http_attempts "
            "FROM agent_budget_reservations "
            "WHERE reservation_id = 'reservation-existing'"
        ).fetchone()
    assert budget == (7, 2, 3)
    assert reservation == (2, 1)


def test_m0i_execution_rows_gain_sequence_and_cannot_be_deleted(
    tmp_path: Path,
) -> None:
    database = tmp_path / "retention.db"
    run_alembic(database, "upgrade", "m0i1d2e3f4a5")
    with sqlite3.connect(database) as connection:
        values = (
            "execution-1", "ctx", "run", "step", 1, "a" * 64,
            "authorization", "reservation", "prepared", 1,
            "2026-09-16 00:00:00", "2026-09-16 00:00:00",
        )
        connection.execute(
            "INSERT INTO agent_external_executions "
            "(execution_id, research_context_id, run_id, step_id, attempt, "
            "request_fingerprint, authorization_id, reservation_id, state, revision, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        connection.commit()
    run_alembic(database, "upgrade", "head")
    with sqlite3.connect(database) as connection:
        sequence = connection.execute(
            "SELECT execution_seq FROM agent_external_executions "
            "WHERE execution_id = 'execution-1'"
        ).fetchone()
        assert sequence == (1,)
        with pytest.raises(sqlite3.IntegrityError, match="ledger retained"):
            connection.execute(
                "DELETE FROM agent_external_executions WHERE execution_id = 'execution-1'"
            )
