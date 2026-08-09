import pytest
from app.modules.feedback.schema import FeedbackCreate
from app.modules.feedback.service import FeedbackService


@pytest.mark.asyncio
async def test_structured_feedback_and_anonymous_export(session):
    service = FeedbackService(session)
    created = await service.create(
        FeedbackCreate(
            task_completion_rate=0.8,
            useful=True,
            citation_correct=False,
            data_correct=True,
            error_type="severe",
            comment="页码不匹配",
            next_step="多论文比较",
        )
    )
    assert created.useful is True and created.citation_correct is False
    exported = await service.anonymous_csv()
    assert (
        "页码不匹配" in exported
        and "user_id" not in exported
        and "email" not in exported
    )


def test_subjective_only_feedback_must_still_have_comment():
    with pytest.raises(ValueError):
        FeedbackCreate(task_completion_rate=0.5)
