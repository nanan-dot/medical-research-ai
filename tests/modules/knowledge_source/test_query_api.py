"""Acceptance tests for knowledge-source paging and persisted preferences."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.modules.knowledge_source.test_api import create_source


def test_page_filters_full_dataset_and_keeps_old_array_contract(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-02/07/15: database filtering precedes paging; legacy list stays an array."""
    for index in range(100):
        root = tmp_path / f"source-{index}"
        root.mkdir()
        response = create_source(
            client, root, "obsidian_vault" if index % 2 else "local_folder"
        )
        assert response.status_code == 201

    old_response = client.get("/api/v1/knowledge-sources", params={"limit": 20})
    page_response = client.get(
        "/api/v1/knowledge-sources/page",
        params={"source_type": "obsidian_vault", "limit": 10},
    )
    summary_response = client.get("/api/v1/knowledge-sources/summary")

    assert isinstance(old_response.json(), list)
    assert len(old_response.json()) == 20
    assert page_response.status_code == 200
    assert page_response.json()["total"] == 50
    assert len(page_response.json()["items"]) == 10
    assert summary_response.status_code == 200
    assert summary_response.json()["source_count"] == 100
    assert summary_response.json()["local_folder_count"] == 50
    assert summary_response.json()["obsidian_count"] == 50


def test_page_sort_is_stable_and_pinned_sources_are_first(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-08: tied values use a stable ID order without page overlap."""
    source_ids = []
    for index in range(6):
        root = tmp_path / f"stable-{index}"
        root.mkdir()
        source_ids.append(create_source(client, root).json()["id"])
    client.patch(
        f"/api/v1/knowledge-sources/{source_ids[-1]}", json={"is_pinned": True}
    )

    first_page = client.get(
        "/api/v1/knowledge-sources/page",
        params={"sort_by": "document_count", "sort_order": "asc", "limit": 3},
    ).json()["items"]
    second_page = client.get(
        "/api/v1/knowledge-sources/page",
        params={
            "sort_by": "document_count",
            "sort_order": "asc",
            "offset": 3,
            "limit": 3,
        },
    ).json()["items"]

    returned_ids = [item["id"] for item in first_page + second_page]
    assert first_page[0]["id"] == source_ids[-1]
    assert len(returned_ids) == len(set(returned_ids)) == 6
    assert set(returned_ids) == set(source_ids)


def test_page_search_escapes_like_and_preferences_are_independent(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-06/09/10: literal LIKE search and independent persisted preferences."""
    root = tmp_path / "folder_100%"
    root.mkdir()
    created = create_source(client, root)
    source_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/knowledge-sources/{source_id}",
        json={"auto_sync": True, "is_pinned": True},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["auto_sync"] is True
    assert updated.json()["is_pinned"] is True
    assert (
        client.get(
            "/api/v1/knowledge-sources/page", params={"q": "folder_100%"}
        ).json()["total"]
        == 1
    )
    assert (
        client.get(
            "/api/v1/knowledge-sources/page", params={"q": "folderX100Y"}
        ).json()["total"]
        == 0
    )
    assert (
        client.get(
            "/api/v1/knowledge-sources/page", params={"q": "x" * 201}
        ).status_code
        == 422
    )
