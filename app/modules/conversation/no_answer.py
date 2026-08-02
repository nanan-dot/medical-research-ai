"""Deterministic insufficient-evidence policy layered over PaperQA2 output."""

from dataclasses import dataclass

from app.integrations.paperqa2 import PaperQAAnswer

NO_ANSWER_TEXT = "当前知识库中没有足够证据。\n建议修改问题、添加论文或扩大检索范围。"
POLICY_VERSION = "no-answer-v1"
LOW_RELEVANCE_THRESHOLD = 0.2
UNCERTAIN_PHRASES = (
    "not enough evidence",
    "insufficient evidence",
    "cannot determine",
    "unclear",
    "无法确定",
    "证据不足",
    "未找到",
    "不清楚",
)


@dataclass(frozen=True)
class AnswerDecision:
    status: str
    uncertainty: float
    reason_codes: list[str]


def evaluate_answer(answers: list[PaperQAAnswer]) -> AnswerDecision:
    sources = [source for answer in answers for source in answer.sources]
    reasons: list[str] = []
    if not sources:
        reasons.append("no_sources")
    scores = [source.score for source in sources if source.score is not None]
    if scores and max(scores) < LOW_RELEVANCE_THRESHOLD:
        reasons.append("low_relevance")
    if any(
        phrase in answer.answer.casefold() for answer in answers for phrase in UNCERTAIN_PHRASES
    ):
        reasons.append("model_uncertain")
    if reasons:
        return AnswerDecision(
            "insufficient_evidence", 1.0 if "no_sources" in reasons else 0.8, reasons
        )
    return AnswerDecision("answered", 0.2, [])
