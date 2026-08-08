from app.modules.ai_disclosure.disclosure_draft import build_disclosure_draft
from app.modules.ai_disclosure.event_normalizer import normalize_event


def test_event_normalizer_keeps_scope_metadata_but_not_sensitive_text() -> None:
    event = normalize_event(
        model_name="local-model",
        model_version="v1",
        purpose="draft",
        input_scope={"papers": 3, "matrices": 2, "user_notes": 1, "text": "secret unpublished data"},
        output_version="v2",
        human_edited=True,
        is_cloud=False,
    )
    assert event.input_scope == "3 篇文献、2 个证据矩阵、1 段用户笔记"
    assert "secret" not in event.input_scope


def test_disclosure_draft_has_responsibility_notice_and_confidential_placeholder() -> None:
    draft = build_disclosure_draft([], confidential=True)
    assert "您对最终内容负责" in draft
    assert "[confidential]" in draft
    assert "不代表适用于所有期刊" in draft
