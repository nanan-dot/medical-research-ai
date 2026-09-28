"""Acceptance coverage for reversible library persistence migration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_library_migration_roundtrip(tmp_path: Path) -> None:
    """AC-LIB-18: a temporary SQLite DB upgrades, downgrades, then upgrades cleanly."""
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'migration.db').as_posix()}"
    environment = {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": ""}
    project_root = Path(__file__).resolve().parents[3]
    # The worktree already has independent user-owned heads.  Exercise only this
    # feature branch rather than merging or modifying unrelated migrations.
    for command in (("upgrade", "i2j3k4l5m6n"), ("downgrade", "-1"), ("upgrade", "i2j3k4l5m6n")):
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", *command],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
