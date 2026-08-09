import pytest

from app.integrations.paperqa2 import PaperQAAnswer, PaperSource
from app.modules.conversation.no_answer import NO_ANSWER_TEXT, evaluate_answer


def answer(text="Strong conclusion", *, sources=None):
    return PaperQAAnswer(answer=text, index_id="idx", sources=sources or [])


@pytest.mark.parametrize("question_number", range(10))
def test_ten_empty_retrieval_cases_are_refused(question_number):
    decision = evaluate_answer([answer(f"Strong unsupported answer {question_number}")])
    assert decision.status == "insufficient_evidence"
    assert decision.reason_codes == ["no_sources"]
    assert NO_ANSWER_TEXT.startswith("当前知识库中没有足够证据")


def test_low_relevance_source_is_refused_even_if_model_is_confident():
    decision = evaluate_answer(
        [answer(sources=[PaperSource(citation="Paper", score=0.1)])]
    )
    assert decision.status == "insufficient_evidence"
    assert "low_relevance" in decision.reason_codes


def test_partial_or_uncertain_answer_is_refused():
    decision = evaluate_answer(
        [
            answer(
                "The first part is supported, but the rest is unclear.",
                sources=[PaperSource(score=0.8)],
            )
        ]
    )
    assert decision.status == "insufficient_evidence"
    assert "model_uncertain" in decision.reason_codes


def test_supported_answer_is_not_over_refused():
    decision = evaluate_answer(
        [answer(sources=[PaperSource(citation="Paper", score=0.8)])]
    )
    assert decision.status == "answered"
    assert decision.reason_codes == []
