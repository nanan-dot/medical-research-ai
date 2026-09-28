"""Acceptance coverage for document-level recent access persistence."""


def test_document_opened_is_persistent_and_idempotent(library_client) -> None:
    """AC-LIB-06: only explicit opened calls update durable recent access."""
    client, seed, _ = library_client
    first_id = seed(relative_path="first.md")
    second_id = seed(relative_path="second.md")

    assert client.get(f"/api/v1/library/items/{first_id}").status_code == 200
    opened = client.post(
        f"/api/v1/library/items/{second_id}/opened",
        json={"idempotency_key": "same-open"},
    )
    assert opened.status_code == 200
    assert client.post(
        f"/api/v1/library/items/{second_id}/opened",
        json={"idempotency_key": "same-open"},
    ).json()["open_count"] == 1
    recent = client.get("/api/v1/library/recent", params={"limit": 10})
    assert recent.status_code == 200
    assert [item["id"] for item in recent.json()["items"]] == [second_id]


def test_document_delete_cascades_access_without_deleting_external_file(library_client) -> None:
    """AC-LIB-16: document deletion removes access metadata but never source files."""
    client, seed, source_root = library_client
    document_id = seed(relative_path="leave-on-disk.md")
    assert client.post(f"/api/v1/library/items/{document_id}/opened").status_code == 200
    assert client.post(f"/api/v1/library/items/{document_id}/repair").status_code == 202
    source_file = next(source_root.rglob("leave-on-disk.md"))
    assert client.delete(f"/api/v1/documents/{document_id}").status_code == 204
    assert source_file.is_file()
    assert client.get("/api/v1/library/recent").json()["total"] == 0
    assert client.get("/api/v1/tasks", params={"status": "queued"}).json()["total"] == 0


def test_recent_is_sql_paged_with_stable_total(library_client) -> None:
    """AC-LIB-06: unseen documents cannot leak into later recent pages."""
    client, seed, _ = library_client
    first_id = seed(relative_path="first-opened.md")
    second_id = seed(relative_path="second-opened.md")
    seed(relative_path="never-opened.md")
    assert client.post(f"/api/v1/library/items/{first_id}/opened").status_code == 200
    assert client.post(f"/api/v1/library/items/{second_id}/opened").status_code == 200

    first = client.get("/api/v1/library/recent", params={"offset": 0, "limit": 1})
    second = client.get("/api/v1/library/recent", params={"offset": 1, "limit": 1})

    assert first.json()["total"] == second.json()["total"] == 2
    assert {first.json()["items"][0]["id"], second.json()["items"][0]["id"]} == {first_id, second_id}
