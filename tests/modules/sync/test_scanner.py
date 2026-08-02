from pathlib import Path

import pytest

from app.modules.knowledge_source.scanner import scan_directory


def test_symlink_alias_is_deduplicated_and_outside_link_is_rejected(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "paper.txt"
    target.write_text("same physical file", encoding="utf-8")
    alias = root / "alias.txt"
    outside = tmp_path / "outside.md"
    outside.write_text("not authorized", encoding="utf-8")
    outside_link = root / "outside.md"
    try:
        alias.symlink_to(target)
        outside_link.symlink_to(outside)
    except OSError:
        pytest.skip("Current Windows account cannot create file symlinks")

    scan = scan_directory(root)
    assert len(scan.files) == 1
    assert scan.skipped_duplicates == 1
    assert scan.failures == 1


def test_directory_disappearing_is_a_failure_not_an_exception(tmp_path: Path):
    missing = tmp_path / "removed"
    scan = scan_directory(missing)
    assert scan.files == {}
    assert scan.failures == 1
    assert scan.failed_prefixes == {""}
