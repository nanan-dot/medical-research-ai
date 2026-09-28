"""A3 schema downgrade safety acceptance."""

import os
import sqlite3
import subprocess
import sys


def test_downgrade_refuses_cross_version_resolved_assets(tmp_path) -> None:
    path = tmp_path / "a3-downgrade.db"
    env = {
        **os.environ,
        "PYTHONPATH": "",
        "DATABASE_URL": f"sqlite+aiosqlite:///{path.as_posix()}",
    }
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stderr[-3000:]
    with sqlite3.connect(path) as database:
        database.execute("PRAGMA foreign_keys=OFF")
        database.execute(
            "INSERT INTO asset_anchor_links "
            "(asset_type,asset_id,original_anchor_id,resolved_anchor_id,resolution_status,resolution_version) "
            "VALUES ('document_annotation',1,101,202,'relocated_verified',2)"
        )
    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "b31a2c4d5e60"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert downgrade.returncode != 0
    assert "DOWNGRADE_WOULD_LOSE_NEW_ASSETS" in downgrade.stderr
