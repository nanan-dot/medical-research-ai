"""Acceptance tests for combining document problem filtering with source filters."""


def test_document_list_accepts_needs_attention_filter(api_context) -> None:
    """AC-11: count and items share the problem predicate."""
    client, _, _ = api_context
    response = client.get("/api/v1/documents", params={"needs_attention": True})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
