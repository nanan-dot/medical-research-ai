"""Acceptance coverage for unified library querying and facets."""

from __future__ import annotations

from app.modules.document.parsers.schemas import ParsedDocument


def _parsed(text: str) -> str:
    return ParsedDocument(source_path="fixture.md", title="Body title", text=text).model_dump_json()


def test_unified_search_matches_all_fields(library_client) -> None:
    """AC-LIB-03: one q finds title, relative path, source and parsed body."""
    client, seed, _ = library_client
    seed(source_name="Clinical notes", relative_path="alpha-file.md")
    seed(relative_path="path-match/second.md")
    seed(relative_path="body.md", parse_status="succeeded", parsed_content=_parsed("needle in body"))

    for query in ("alpha-file", "path-match", "Clinical notes", "needle"):
        response = client.get("/api/v1/library/items", params={"q": query})
        assert response.status_code == 200
        assert response.json()["total"] >= 1
        assert isinstance(response.json()["items"], list)

    body_item = client.get("/api/v1/library/items", params={"q": "needle"}).json()["items"][0]
    assert "content" in body_item["match_fields"]
    assert "needle" in body_item["snippet"].casefold()


def test_filters_sorting_and_facets_are_global(library_client) -> None:
    """AC-LIB-04/17: filters precede paging, LIKE is literal, facets exclude self filter."""
    client, seed, _ = library_client
    seed(source_name="Folder_100%", relative_path="a.pdf", parse_status="succeeded", index_status="succeeded", index_key="a")
    seed(source_name="Folder_100%", relative_path="b.docx", parse_status="failed")
    seed(source_name="Vault", source_type="obsidian_vault", relative_path="c.md")

    literal = client.get("/api/v1/library/items", params={"q": "Folder_100%", "limit": 1})
    assert literal.status_code == 200
    assert literal.json()["total"] == 2
    assert client.get("/api/v1/library/items", params={"q": "FolderX100Y"}).json()["total"] == 0
    assert client.get("/api/v1/library/items", params={"q": "x" * 201}).status_code == 422

    page_one = client.get("/api/v1/library/items", params={"sort_by": "name", "limit": 2}).json()
    page_two = client.get("/api/v1/library/items", params={"sort_by": "name", "offset": 2, "limit": 2}).json()
    ids = [item["id"] for item in page_one["items"] + page_two["items"]]
    assert len(ids) == len(set(ids)) == 3
    facets = client.get("/api/v1/library/facets", params={"file_type": "pdf"})
    assert facets.status_code == 200
    assert sum(item["count"] for item in facets.json()["file_types"]) == 3
