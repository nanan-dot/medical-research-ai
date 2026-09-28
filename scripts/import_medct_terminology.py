"""Build the local bounded-lookup index from the Apache-2.0 MedCT package."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

_HAN = re.compile(r"[\u3400-\u9fff]")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’-]*")


def _normalize_english(value: str) -> str:
    return " ".join(match.group(0).lower().replace("’", "'") for match in _WORD.finditer(value))


def build_index(source_dir: Path, output_path: Path) -> tuple[int, int]:
    files = sorted(source_dir.glob("*_sctid_syn-enzh.json"))
    if not files:
        raise SystemExit(f"No MedCT JSON files found in {source_dir}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(output_path)
    with connection:
        connection.executescript(
            "DROP TABLE IF EXISTS terms; DROP TABLE IF EXISTS metadata;"
            "CREATE TABLE terms(source_term TEXT PRIMARY KEY,target_term TEXT NOT NULL,"
            "concept_id TEXT NOT NULL,category TEXT NOT NULL,word_count INTEGER NOT NULL);"
            "CREATE INDEX ix_terms_word_count ON terms(word_count);"
            "CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);"
        )
        concepts = 0
        terms = 0
        for path in files:
            category = path.name.split("_", 1)[0]
            payload = json.loads(path.read_text(encoding="utf-8"))
            concepts += len(payload)
            for concept_id, synonyms in payload.items():
                chinese_values = [value.strip() for value in synonyms if _HAN.search(value)]
                chinese = min(
                    chinese_values,
                    key=lambda value: (
                        bool(re.search(r"[A-Za-z]", value)),
                        bool(re.search(r"[-—_]", value)),
                        "结构" in value,
                        len(value),
                    ),
                    default=None,
                )
                if not chinese:
                    continue
                for value in synonyms:
                    if _HAN.search(value):
                        continue
                    normalized = _normalize_english(value)
                    if not normalized:
                        continue
                    cursor = connection.execute(
                        "INSERT OR IGNORE INTO terms VALUES(?,?,?,?,?)",
                        (normalized, chinese, concept_id, category, len(normalized.split())),
                    )
                    terms += cursor.rowcount
        metadata = {
            "dataset": "TigerResearch/MedCT",
            "source": "https://huggingface.co/datasets/TigerResearch/MedCT",
            "declared_license": "Apache-2.0",
            "concept_count": str(concepts),
            "term_count": str(terms),
        }
        connection.executemany("INSERT INTO metadata VALUES(?,?)", metadata.items())
    connection.close()
    return concepts, terms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    concepts, terms = build_index(args.source_dir, args.output_path)
    print(json.dumps({"concepts": concepts, "terms": terms, "index": str(args.output_path)}))


if __name__ == "__main__":
    main()
