import pytest

from app.modules.evidence_writing.polish_guard import extract_protected_tokens, validate_polish
from app.modules.evidence_writing.sentence_marker import validate_segments
from app.modules.evidence_writing.state_machine import transition


def test_state_machine_requires_outline_confirmation() -> None:
    with pytest.raises(ValueError):
        transition("drafting", "generate_draft")
    assert transition("drafting", "submit_outline") == "outline_pending"
    assert transition("outline_pending", "confirm_outline") == "outline_confirmed"
    assert transition("outline_confirmed", "generate_draft") == "drafting"


def test_sentence_markers_require_citation_for_evidence_and_pending_item() -> None:
    valid = [
        {"text": "用户数据", "origin": "user_provided", "citation_ids": []},
        {"text": "论文结论", "origin": "paper_evidence", "citation_ids": ["pmid:1"]},
        {"text": "待核实", "origin": "pending", "citation_ids": [], "pending_item_id": "p1"},
    ]
    assert len(validate_segments(valid, pending_item_ids={"p1"})) == 3
    with pytest.raises(ValueError):
        validate_segments([{ "text": "无标记", "origin": "" }], pending_item_ids=set())


def test_polish_guard_rejects_changed_numbers_and_citations() -> None:
    original = "样本量为 42，引用 PMID:123。"
    assert validate_polish(original, "样本量为 42，引用 PMID:123。") == []
    assert extract_protected_tokens(original)
    with pytest.raises(ValueError, match="protected"):
        validate_polish(original, "样本量为 43，引用 PMID:999。")
    with pytest.raises(ValueError, match="protected"):
        validate_polish("2023年纳入42例", "2022年纳入42例")
    with pytest.raises(ValueError, match="protected"):
        validate_polish("纳入42例，对照10例", "纳入10例，对照42例")
