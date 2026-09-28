"""Acceptance coverage for server-owned source trees."""


def test_source_tree_counts_and_node_filter(library_client) -> None:
    """AC-LIB-05: tree direct/descendant counts use all rows and normalize Windows paths."""
    client, seed, _ = library_client
    seed(source_name="Local", relative_path="A\\Shared\\one.md")
    seed(source_name="Local", relative_path="a/shared/deep/two.md")
    seed(source_name="Vault", source_type="obsidian_vault", relative_path="notes/one.md")

    response = client.get("/api/v1/library/source-tree")
    assert response.status_code == 200
    groups = {group["source_type"]: group for group in response.json()["groups"]}
    assert groups["local"]["descendant_count"] == 2
    local_source = groups["local"]["children"][0]
    shared = next(node for node in local_source["children"] if node["name"].casefold() == "a")
    assert shared["descendant_count"] == 2
    filtered = client.get("/api/v1/library/items", params={"tree_node_id": shared["node_id"]})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2
