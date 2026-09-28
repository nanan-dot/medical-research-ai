"""真实 Alembic 历史升级与 A0 schema 往返，隔离生产数据库。"""

import os
import sqlite3
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_a0_migrations_roundtrip_without_losing_preexisting_data(tmp_path):
    expected_head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    path = tmp_path / "migration.db"
    env = {
        **os.environ,
        "PYTHONPATH": "",
        "DATABASE_URL": f"sqlite+aiosqlite:///{path.as_posix()}",
    }

    def migrate(target, direction="upgrade"):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", direction, target],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert result.returncode == 0, result.stderr[-3000:]

    migrate("m4n5o6p7q8r9")
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE a0_preexisting_sentinel (value TEXT NOT NULL)")
        db.execute("INSERT INTO a0_preexisting_sentinel VALUES ('preserve')")
    migrate("head")
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            == expected_head
        )
        assert "char_map_json" in {
            row[1] for row in db.execute("PRAGMA table_info(document_source_pages)")
        }
        assert "uq_anchor_current_document" in {
            row[1] for row in db.execute("PRAGMA index_list(document_anchor_revisions)")
        }
    migrate("m4n5o6p7q8r9", "downgrade")
    migrate("head")
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT value FROM a0_preexisting_sentinel").fetchone()[0]
            == "preserve"
        )
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
