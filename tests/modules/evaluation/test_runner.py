from app.modules.evaluation.dataset import EvaluationQuestion
from app.modules.evaluation.runner import (
    EvaluationConfig,
    EvaluationRun,
    QuestionRun,
    execute,
)


def question(question_id: str) -> EvaluationQuestion:
    return EvaluationQuestion(question_id=question_id, question="Q", answer="A", evidence_document_id=1, question_type="result", difficulty="easy", review_status="approved", dataset_version="v1", split="test")

def run() -> EvaluationRun:
    return EvaluationRun(EvaluationConfig("v1", {"top_k": 5}, {"name": "local"}, "p1"))

def test_records_failure_and_continues() -> None:
    def executor(item: EvaluationQuestion) -> str:
        if item.question_id == "bad": raise RuntimeError("expected")
        return "output"
    result = execute(run(), [question("ok"), question("bad")], executor)
    assert result.status == "completed"
    assert [item.status for item in result.records] == ["completed", "failed"]

def test_resume_skips_existing_records() -> None:
    state = run(); state.status = "failed"; state.records.append(QuestionRun("one", "completed", "first", 1))
    execute(state, [question("one"), question("two")], lambda _: "second")
    assert [item.question_id for item in state.records] == ["one", "two"]

def test_cancellation_preserves_completed_records() -> None:
    state = execute(run(), [question("one"), question("two")], lambda _: "out", cancel_requested=lambda: True)
    assert state.status == "cancelled" and not state.records
