"""Versioned server-owned confirmation action to role policy."""

CONFIRMATION_POLICY_VERSION = "m0-confirmation-policy-v1"

ACTION_REQUIRED_ROLE: dict[str, str] = {
    "approve_draft": "user_owner",
    "approve_literature_selection": "user_owner",
    "confirm_evidence": "user_owner",
    "confirm_report_link": "user_owner",
    "confirm_synthesis": "user_owner",
    "approve_study_design": "user_owner",
    "approve_submission_package": "author_responsible",
    "approve_medical_review": "medical_reviewer",
    "approve_statistical_review": "statistical_reviewer",
    "approve_render_review": "render_reviewer",
}
CONFIRMATION_POLICIES = {CONFIRMATION_POLICY_VERSION: ACTION_REQUIRED_ROLE}


def required_role_for(
    action: str, policy_version: str = CONFIRMATION_POLICY_VERSION
) -> str:
    try:
        return CONFIRMATION_POLICIES[policy_version][action]
    except KeyError as exc:
        raise ValueError(
            f"unknown confirmation policy/action: {policy_version}/{action}"
        ) from exc
