"""Align strategy fingerprints with actual PubMed conditions.

Revision ID: j3c4d5e6f7a
Revises: i2b3c4d5e6f
Create Date: 2026-08-13
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j3c4d5e6f7a"
down_revision: str | Sequence[str] | None = "i2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _canonical_json(value: str) -> object | str:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _strategy_fingerprint(row: sa.RowMapping) -> str:
    """Match runtime identity from the actual PubMed conditions only.

    The task's parsed candidate, model version, edits and retmax are audit inputs.
    Once they resolve to the same query and filters, they must not split the user-
    facing research record.
    """
    snapshot = {
        "database": row["database"],
        "search_string": row["search_string"],
        "filters": _canonical_json(row["filters"]),
    }
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """Recompute existing fingerprints without deleting audit snapshots."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, search_string, database, filters "
            "FROM literature_search_tasks"
        )
    ).mappings()
    for row in rows:
        connection.execute(
            sa.text(
                "UPDATE literature_search_tasks "
                "SET strategy_fingerprint = :fingerprint WHERE id = :task_id"
            ),
            {"fingerprint": _strategy_fingerprint(row), "task_id": row["id"]},
        )


def downgrade() -> None:
    """Keep upgraded fingerprints; downgrading must not discard audit rows."""
