"""Acceptance coverage for safe library error contracts."""


def test_library_errors_do_not_leak_paths_or_credentials(library_client, tmp_path) -> None:
    """AC-LIB-17: user-visible errors are stable and do not disclose absolute paths."""
    client, _, _ = library_client
    missing = client.get("/api/v1/library/items/999999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert str(tmp_path) not in missing.text
    assert "api_key" not in missing.text.casefold()
