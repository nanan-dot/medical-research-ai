from app.core.config import Settings


def test_medical_shadow_performance_budget_is_unapproved_by_default() -> None:
    settings = Settings()
    assert settings.MEDICAL_SHADOW_PERFORMANCE_BUDGET_APPROVED is False
    assert settings.MEDICAL_SHADOW_PERFORMANCE_BUDGET_SOURCE == ""
