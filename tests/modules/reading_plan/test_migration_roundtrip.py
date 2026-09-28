"""Executable migration gate for structured reading-plan reasons."""

import os
import sqlite3
import subprocess
import sys


def _alembic(revision: str, database_url: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )


def _downgrade(revision: str, database_url: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", revision],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_reading_reason_migration_archives_duplicate_active_and_roundtrips(tmp_path) -> None:
    database = tmp_path / "migration.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    _alembic("e8f9a0b1c2d3", database_url)

    with sqlite3.connect(database) as connection:
        base_plan = (
            1,
            "active",
            "legacy",
            "{}",
            "all",
            12,
        )
        connection.execute(
            "INSERT INTO reading_plans "
            "(result_id, version, status, algorithm_version, generation_basis_json, "
            "duplicate_mode, target_core_count) VALUES (?, 1, ?, ?, ?, ?, ?)",
            base_plan,
        )
        connection.execute(
            "INSERT INTO reading_plans "
            "(result_id, version, status, algorithm_version, generation_basis_json, "
            "duplicate_mode, target_core_count) VALUES (?, 2, ?, ?, ?, ?, ?)",
            base_plan,
        )
        connection.execute(
            "INSERT INTO reading_plan_items "
            "(plan_id, pmid, stage, role, stage_order, recommendation_reason, "
            "evidence_features_json, limitations_json, source, is_locked) "
            "VALUES (2, '123', 'overview', 'core', 0, 'legacy reason', '{}', '[]', "
            "'system', 0)"
        )

    _alembic("head", database_url)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM reading_plans WHERE result_id = 1 AND status = 'active'"
        ).fetchone()[0] == 1
        reason = connection.execute(
            "SELECT reading_reason_json FROM reading_plan_items WHERE pmid = '123'"
        ).fetchone()[0]
        assert '"status": "partial"' in reason
        assert "legacy reason" in reason

    _downgrade("e8f9a0b1c2d3", database_url)
    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(reading_plan_items)")
        }
        assert "reading_reason_json" not in columns

    _alembic("head", database_url)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
