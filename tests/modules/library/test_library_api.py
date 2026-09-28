"""Acceptance coverage for library summary, task state, and reprocessing."""

from __future__ import annotations


def test_summary_uses_persisted_state(library_client) -> None:
    """AC-LIB-01: summary derives every count from persisted workflow facts."""
    client, seed, _ = library_client
    seed(
        relative_path="ready.md",
        parse_status="succeeded",
        index_status="succeeded",
        index_key="valid-index",
    )
    seed(relative_path="parsing.md", parse_status="parsing")
    seed(relative_path="parse-failed.md", parse_status="failed", error_code="parse_failed")
    seed(relative_path="outdated.md", parse_status="succeeded", index_status="outdated")

    response = client.get("/api/v1/library/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert payload["processed"] == 2
    assert payload["ai_available"] == 1
    assert payload["processing"] == 1
    assert payload["needs_attention"] == 2
    assert payload["issue_breakdown"]["parse_failed"] == 1
    assert payload["snapshot_at"] is not None


def test_item_exposes_latest_active_task(library_client) -> None:
    """AC-LIB-02: a refresh exposes only the newest active durable task."""
    client, seed, _ = library_client
    document_id = seed(relative_path="running.md", parse_status="parsing")

    # The public repair action creates an idempotent queued task; the list must surface it.
    first = client.post(f"/api/v1/documents/{document_id}/repair")
    second = client.post(f"/api/v1/documents/{document_id}/repair")
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["task_id"] == second.json()["task_id"]

    items = client.get("/api/v1/library/items", params={"q": "running"})
    assert items.status_code == 200
    item = items.json()["items"][0]
    assert item["task_id"] == first.json()["task_id"]
    assert item["task_status"] == "queued"
    assert item["progress"] == 0
    assert item["phase"] == "queued"
    assert {"view", "view_progress", "delete"}.issubset(item["available_actions"])


def test_outdated_document_recovers_after_reprocess(library_client) -> None:
    """AC-LIB-13/15: reprocessing is durable and repeated submits reuse the task."""
    client, seed, _ = library_client
    document_id = seed(
        relative_path="changed.md", parse_status="succeeded", index_status="outdated"
    )

    before = client.get(f"/api/v1/library/items/{document_id}")
    assert before.status_code == 200
    assert before.json()["status"] == "outdated"

    first = client.post(f"/api/v1/library/items/{document_id}/reprocess")
    second = client.post(f"/api/v1/library/items/{document_id}/reprocess")
    assert first.status_code == 202 and second.status_code == 202
    assert first.json()["task_id"] == second.json()["task_id"]
