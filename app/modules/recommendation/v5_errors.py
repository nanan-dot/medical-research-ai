"""Stable error attribution for durable recommendation runs."""

from app.integrations.pubmed.exceptions import PubMedError


def classify_run_error(error: Exception, *, stage: str) -> dict[str, str | None]:
    if isinstance(error, PubMedError) or stage == "pubmed_collection":
        return {
            "code": "candidate_collection_failed",
            "message": str(error),
            "provider": "pubmed",
        }
    if stage == "input_decode" or isinstance(error, (ValueError, TypeError)):
        return {
            "code": "recommendation_input_invalid",
            "message": str(error),
            "provider": None,
        }
    return {
        "code": "recommendation_execution_failed",
        "message": str(error),
        "provider": None,
    }
