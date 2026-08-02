"""Bounded, authorization-aware recursive file scanning."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.common.path_utils import is_within_root, normalized_path_key

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".docx", ".txt"})
IGNORED_DIRECTORIES = frozenset({".obsidian", ".git", ".trash"})


@dataclass(frozen=True, slots=True)
class ScannedFile:
    path: Path
    relative_path: str
    normalized_relative_path: str
    file_size: int
    modified_time_ns: int


@dataclass(slots=True)
class DirectoryScan:
    files: dict[str, ScannedFile] = field(default_factory=dict)
    failed_paths: set[str] = field(default_factory=set)
    failed_prefixes: set[str] = field(default_factory=set)
    skipped_duplicates: int = 0
    failures: int = 0


def scan_directory(root_path: Path) -> DirectoryScan:
    result = DirectoryScan()
    try:
        root = root_path.resolve(strict=True)
    except OSError:
        result.failed_prefixes.add("")
        result.failures = 1
        return result
    visited_directories: set[str] = set()
    seen_files: set[tuple[int, int] | str] = set()

    def walk(directory: Path) -> None:
        directory_key = normalized_path_key(directory)
        if directory_key in visited_directories:
            return
        visited_directories.add(directory_key)
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        except OSError:
            try:
                prefix = str(directory.relative_to(root))
            except ValueError:
                prefix = ""
            result.failed_prefixes.add(os.path.normcase(os.path.normpath(prefix)))
            result.failures += 1
            return

        for entry in entries:
            if entry.name.casefold() in IGNORED_DIRECTORIES:
                continue
            raw_path = Path(entry.path)
            relative_hint = os.path.normcase(os.path.normpath(str(raw_path.relative_to(root))))
            try:
                resolved = raw_path.resolve(strict=True)
                if not is_within_root(resolved, root):
                    result.failed_paths.add(relative_hint)
                    result.failures += 1
                    continue
                if entry.is_dir(follow_symlinks=True):
                    walk(resolved)
                    continue
                if not entry.is_file(follow_symlinks=True):
                    continue
                if resolved.suffix.casefold() not in SUPPORTED_SUFFIXES:
                    continue
                stat = resolved.stat()
            except OSError:
                result.failed_paths.add(relative_hint)
                result.failures += 1
                continue

            identity: tuple[int, int] | str
            identity = (stat.st_dev, stat.st_ino) if stat.st_ino else normalized_path_key(resolved)
            if identity in seen_files:
                result.skipped_duplicates += 1
                continue
            seen_files.add(identity)
            relative_path = str(resolved.relative_to(root))
            normalized_relative = os.path.normcase(os.path.normpath(relative_path))
            result.files[normalized_relative] = ScannedFile(
                path=resolved,
                relative_path=relative_path,
                normalized_relative_path=normalized_relative,
                file_size=stat.st_size,
                modified_time_ns=stat.st_mtime_ns,
            )

    walk(root)
    return result
