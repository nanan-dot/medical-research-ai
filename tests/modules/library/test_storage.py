"""Acceptance coverage for database-aggregated storage reporting."""

from __future__ import annotations

from io import BytesIO


def test_storage_separates_managed_and_external_bytes(library_client, monkeypatch) -> None:
    """AC-LIB-09: no quota is invented; managed and referenced bytes stay distinct."""
    client, seed, _ = library_client
    external_id = seed(relative_path="external.md", file_bytes=b"external-bytes")
    upload = client.post(
        "/api/v1/library/imports",
        files=[("files", ("managed.md", BytesIO(b"managed"), "text/markdown"))],
    )
    assert upload.status_code == 201
    result = client.get("/api/v1/library/storage")
    assert result.status_code == 200
    payload = result.json()
    assert payload["managed_bytes"] == 7
    assert payload["external_source_bytes"] == len(b"external-bytes")
    assert payload["quota_bytes"] is None
    assert payload["usage_percent"] is None
    assert payload["status"] == "not_configured"
    assert payload["measured_at"] is not None
    assert client.get(f"/api/v1/library/items/{external_id}").status_code == 200

    monkeypatch.setattr("app.core.config.settings.LIBRARY_STORAGE_QUOTA_BYTES", 5)
    exceeded = client.post("/api/v1/library/storage/refresh")
    assert exceeded.status_code == 200
    assert exceeded.json()["status"] == "exceeded"
