"""Bounded lookup over an offline English-Chinese medical terminology index."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’-]*")


class MedicalTerminologyDataset:
    def __init__(self, index_path: Path, *, max_phrase_words: int = 12) -> None:
        self._index_path = index_path
        self._max_phrase_words = max_phrase_words

    @property
    def available(self) -> bool:
        return self._index_path.is_file()

    def lookup(
        self,
        source_text: str,
        *,
        limit: int = 48,
        reserved_terms: tuple[str, ...] = (),
    ) -> dict[str, str]:
        if not self.available:
            return {}
        words = [match.group(0).lower().replace("’", "'") for match in _WORD.finditer(source_text)]
        phrases = {
            " ".join(words[start:end])
            for start in range(len(words))
            for end in range(start + 1, min(len(words), start + self._max_phrase_words) + 1)
        }
        if not phrases:
            return {}
        found: dict[str, tuple[str, int]] = {}
        ordered = sorted(phrases)
        with sqlite3.connect(f"file:{self._index_path.as_posix()}?mode=ro", uri=True) as connection:
            for offset in range(0, len(ordered), 800):
                batch = ordered[offset:offset + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT source_term, target_term, word_count FROM terms "
                    f"WHERE source_term IN ({placeholders})",
                    batch,
                )
                for source_term, target_term, word_count in rows:
                    found[source_term] = (target_term, word_count)
        occupied: set[int] = set()
        for term in reserved_terms:
            needle = [match.group(0).lower().replace("’", "'") for match in _WORD.finditer(term)]
            for start in range(len(words) - len(needle) + 1):
                if words[start:start + len(needle)] == needle:
                    occupied.update(range(start, start + len(needle)))
        selected: dict[str, str] = {}
        for source, (target, word_count) in sorted(
            found.items(), key=lambda item: (-item[1][1], -len(item[0]))
        ):
            needle = source.split()
            span = next(
                (
                    set(range(start, start + word_count))
                    for start in range(len(words) - word_count + 1)
                    if words[start:start + word_count] == needle
                    and not occupied.intersection(range(start, start + word_count))
                ),
                None,
            )
            if span is None:
                continue
            selected[source] = target
            occupied.update(span)
            if len(selected) >= limit:
                break
        return selected
