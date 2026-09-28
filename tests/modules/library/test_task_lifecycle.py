"""Acceptance coverage for durable document task transitions."""


def test_document_task_lifecycle_is_idempotent(library_client) -> None:
    """AC-LIB-15: queued work is observable, cancellable and retry-safe."""
    client, seed, _ = library_client
    document_id = seed(relative_path="broken.md", parse_status="failed")
    accepted = client.post(f"/api/v1/library/items/{document_id}/repair")
    assert accepted.status_code == 202
    task_id = accepted.json()["task_id"]
    assert client.post(f"/api/v1/library/items/{document_id}/repair").json()["task_id"] == task_id
    cancelled = client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
