from pathlib import Path

import pytest

from app.modules.evaluation.dataset import load_jsonl


def write_dataset(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "test.jsonl"; path.write_text("\n".join(lines), encoding="utf-8"); return path

def test_loads_versioned_annotation_dataset(tmp_path: Path) -> None:
    path = write_dataset(tmp_path, ['{"question_id":"q1","question":"样本量？","answer":"100","evidence_document_id":1,"page":2,"section":"Results","question_type":"sample_size","difficulty":"easy","review_status":"approved","dataset_version":"v1","split":"test"}'])
    dataset = load_jsonl(path, split="test")
    assert dataset.version == "v1" and len(dataset.sha256) == 64

def test_rejects_duplicate_question_ids(tmp_path: Path) -> None:
    line = '{"question_id":"q1","question":"Q","answer":"A","evidence_document_id":1,"question_type":"result","difficulty":"easy","review_status":"approved","dataset_version":"v1","split":"test"}'
    with pytest.raises(ValueError, match="duplicate"):
        load_jsonl(write_dataset(tmp_path, [line, line]), split="test")

def test_allows_no_answer_without_evidence(tmp_path: Path) -> None:
    line = '{"question_id":"q2","question":"Q","no_answer":true,"question_type":"no_answer","difficulty":"hard","review_status":"reviewed","dataset_version":"v1","split":"development"}'
    assert load_jsonl(write_dataset(tmp_path, [line]), split="development").questions[0].no_answer
