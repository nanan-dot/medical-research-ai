"""Rebuild canonical literature strategy fingerprints for history projection.

Revision ID: i2b3c4d5e6f
Revises: h1a2b3c4d5e6
Create Date: 2026-08-13
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "h1a2b3c4d5e6"
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
    normalized = _normalize_user_edit_value(parsed)
    return json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _strategy_fingerprint(row: sa.RowMapping) -> str:
    """Match the runtime strategy identity without importing application code.

    Alembic revisions must remain executable after future service refactors. retmax
    intentionally stays out of this identity because it limits one response batch,
    not the PubMed conditions that define the research strategy.
    """
    snapshot = {
        "database": row["database"],
        "search_string": row["search_string"],
        "filters": _canonical_json(row["filters"]),
        "user_edits": _normalize_user_edits(row["user_edits"]),
        "model_version": row["model_version"],
        "structured_query": _canonical_json(row["structured_query"]),
        "original_query": row["original_query"],
    }
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """Backfill every audit row and allow many snapshots per strategy."""
    op.drop_index(
        "ix_literature_search_tasks_strategy_fingerprint",
        table_name="literature_search_tasks",
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, original_query, structured_query, search_string, database, "
            "filters, model_version, user_edits FROM literature_search_tasks"
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

    op.create_index(
        "ix_literature_search_tasks_strategy_history",
        "literature_search_tasks",
        ["strategy_fingerprint", "searched_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Restore the prior nullable unique index without deleting audit data."""
    op.drop_index(
        "ix_literature_search_tasks_strategy_history",
        table_name="literature_search_tasks",
    )
    op.create_index(
        "ix_literature_search_tasks_strategy_fingerprint",
        "literature_search_tasks",
        ["strategy_fingerprint"],
        unique=True,
    )
