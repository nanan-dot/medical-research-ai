"""AC-PCB-18 migration round-trip against an isolated database."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def _alembic(repo: Path, database: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = ""
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(repo / "alembic.ini"), *arguments],
        cwd=repo,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_paper_center_migration_upgrade_downgrade_upgrade_and_check(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[3]
    database = tmp_path / "paper_center_migration.db"

    _alembic(repo, database, "upgrade", "head")
    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(paper_research_center_preferences)"
            )
        }
        activity_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(paper_activities)")
        }
    assert {"actor_scope", "research_context_id", "stage", "version"} <= columns
    assert "actor_scope" in activity_columns

    _alembic(repo, database, "downgrade", "s2f3g4h5i6j7")
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "paper_research_center_preferences" not in tables

    _alembic(repo, database, "upgrade", "head")
    _alembic(repo, database, "check")
