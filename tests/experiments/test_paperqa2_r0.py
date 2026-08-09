from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.paperqa2_r0.run import (
    ExperimentInputError,
    load_trusted_index,
    sanitize_session,
    save_trusted_index,
    validate_pdf,
    write_json,
)


def test_validate_pdf_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ExperimentInputError, match="does not exist"):
        validate_pdf(tmp_path / "missing.pdf")


def test_trusted_index_round_trip_and_metadata_guard(tmp_path: Path) -> None:
    root = tmp_path / "index"
    path = root / "docs.pkl"
    metadata = {"paperqa_version": "fixed", "pdf_sha256": "abc"}
    save_trusted_index(path, root, {"chunks": 3}, metadata)
    assert load_trusted_index(path, root, metadata) == {"chunks": 3}
    with pytest.raises(ExperimentInputError, match="metadata"):
        load_trusted_index(path, root, {**metadata, "pdf_sha256": "changed"})


def test_trusted_index_cannot_escape_data_root(tmp_path: Path) -> None:
    with pytest.raises(ExperimentInputError, match="must remain"):
        save_trusted_index(tmp_path / "outside.pkl", tmp_path / "inside", {}, {})


@dataclass
class FakeContext:
    text: object
    context: str
    score: float


def test_sanitized_raw_result_preserves_source_and_page_then_saves(
    tmp_path: Path,
) -> None:
    document = SimpleNamespace(title="A medical paper", citation="Journal (2023)")
    text = SimpleNamespace(
        doc=document, name="paper pages 11-12", text="507 events: 233 and 274."
    )
    session = SimpleNamespace(
        question="How many?",
        answer="There were 507 events: 233 intervention and 274 usual care.",
        raw_answer="The values were 507, 233, and 274.",
        formatted_answer="Answer with citation.",
        has_successful_answer=True,
        contexts=[FakeContext(text, text.text, 0.9)],
        used_contexts=[0],
    )
    result = sanitize_session(
        session, run_metadata={}, index_metadata={"reused": False}
    )
    assert result["capabilities"] == {
        "nonempty_answer": True,
        "source_count": 1,
        "paper_title_present": True,
        "page_range_present": True,
        "expected_values_present": True,
        "manual_source_pdf_page": 11,
    }
    assert result["sources"][0]["page_range"] == "11-12"
    output = tmp_path / "result.json"
    write_json(output, result)
    assert '"schema_version": "1.0"' in output.read_text(encoding="utf-8")
