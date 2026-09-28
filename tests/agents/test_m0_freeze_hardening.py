"""Release-hardening gates required by the M0 freeze review."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]


def clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return environment


def test_fastapi_testclient_import_has_no_deprecation_warning() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            "from fastapi.testclient import TestClient; assert TestClient",
        ],
        cwd=REPO_ROOT,
        env=clean_environment(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_begin_immediate_preserves_all_multiprocess_writes(tmp_path: Path) -> None:
    database = tmp_path / "contention.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE m0_contention_probe "
            "(id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO m0_contention_probe (id, value) VALUES (1, 0)"
        )
        connection.commit()

    worker = Path(__file__).with_name("sqlite_contention_worker.py")
    process_count = 4
    writes_per_process = 20
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(worker),
                str(database),
                str(writes_per_process),
            ],
            cwd=REPO_ROOT,
            env=clean_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(process_count)
    ]
    failures: list[str] = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=60)
        if process.returncode != 0:
            failures.append(stderr or stdout)
    assert failures == []

    with sqlite3.connect(database) as connection:
        value = connection.execute(
            "SELECT value FROM m0_contention_probe WHERE id = 1"
        ).fetchone()
    assert value == (process_count * writes_per_process,)
