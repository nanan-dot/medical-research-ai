"""Separate exact task identity from history read-model identity.

Revision ID: k4d5e6f7a8b
Revises: j3c4d5e6f7a
Create Date: 2026-08-13
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k4d5e6f7a8b"
down_revision: str | Sequence[str] | None = "j3c4d5e6f7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _canonical_json(value: str) -> object | str:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _normalize_user_edit_value(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        normalized_items = [_normalize_user_edit_value(item) for item in value]
        return sorted(
            (item for item in normalized_items if item != ""),
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    if isinstance(value, dict):
        return {
            key: _normalize_user_edit_value(item)
            for key, item in sorted(value.items())
        }
    return value


def _normalize_user_edits(raw: str) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    return json.dumps(
        _normalize_user_edit_value(parsed),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _fingerprint(snapshot: dict[str, object]) -> str:
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _task_fingerprint(row: sa.RowMapping) -> str:
    """Preserve the original exact task identity for reuse and deduplication."""
    return _fingerprint(
        {
            "database": row["database"],
            "search_string": row["search_string"],
            "filters": _canonical_json(row["filters"]),
            "retmax": row["retmax"],
            "user_edits": _normalize_user_edits(row["user_edits"]),
            "model_version": row["model_version"],
            "structured_query": _canonical_json(row["structured_query"]),
            "original_query": row["original_query"],
        }
    )


def _history_fingerprint(row: sa.RowMapping) -> str:
    """Group history by the actual PubMed conditions, not audit process inputs."""
    return _fingerprint(
        {
            "database": row["database"],
            "search_string": row["search_string"],
            "filters": _canonical_json(row["filters"]),
        }
    )


def upgrade() -> None:
    """Backfill two identities without deleting tasks, snapshots or user state."""
    op.add_column(
        "literature_search_tasks",
        sa.Column("history_fingerprint", sa.Text(), nullable=True),
    )
    op.drop_index(
        "ix_literature_search_tasks_strategy_history",
        table_name="literature_search_tasks",
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, original_query, structured_query, search_string, database, "
            "filters, retmax, model_version, user_edits FROM literature_search_tasks"
        )
    ).mappings()
    for row in rows:
        connection.execute(
            sa.text(
                "UPDATE literature_search_tasks "
                "SET strategy_fingerprint = :task_fingerprint, "
                "history_fingerprint = :history_fingerprint "
                "WHERE id = :task_id"
            ),
            {
                "task_fingerprint": _task_fingerprint(row),
                "history_fingerprint": _history_fingerprint(row),
                "task_id": row["id"],
            },
        )

    op.create_index(
        "ix_literature_search_tasks_strategy_history",
        "literature_search_tasks",
        ["history_fingerprint", "searched_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only the read-model identity; audit tasks and snapshots remain."""
    op.drop_index(
        "ix_literature_search_tasks_strategy_history",
        table_name="literature_search_tasks",
    )
    op.drop_column("literature_search_tasks", "history_fingerprint")
    op.create_index(
        "ix_literature_search_tasks_strategy_history",
        "literature_search_tasks",
        ["strategy_fingerprint", "searched_at", "id"],
        unique=False,
    )
