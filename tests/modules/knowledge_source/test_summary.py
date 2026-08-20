"""Acceptance tests for SQL-backed knowledge-base summary."""

from fastapi.testclient import TestClient


def test_empty_summary_has_zero_counts_and_null_percent(client: TestClient) -> None:
    """AC-01: empty databases never manufacture availability statistics."""
    response = client.get("/api/v1/knowledge-sources/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_count"] == 0
    assert payload["total_item_count"] == 0
    assert payload["availability_percent"] is None
    assert payload["issue_breakdown"] == {
        "parse_failed": 0,
        "unsupported_format": 0,
        "unavailable_file": 0,
        "index_failed": 0,
        "other": 0,
    }


def test_static_page_and_summary_routes_are_not_captured_as_ids(
    client: TestClient,
) -> None:
    """AC-17: static knowledge-source routes resolve before /{id}."""
    assert client.get("/api/v1/knowledge-sources/page").status_code == 200
    assert client.get("/api/v1/knowledge-sources/summary").status_code == 200
