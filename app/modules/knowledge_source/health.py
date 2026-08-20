"""Pure knowledge-source health classification rules."""


def health_status(
    enabled: bool, sync_status: str, failed_count: int, has_completed_errors: bool
) -> str:
    """Return the UI health state from persisted source and document state."""
    if not enabled:
        return "paused"
    if sync_status == "unavailable":
        return "unavailable"
    if sync_status == "scanning":
        return "syncing"
    if (
        failed_count > 0
        or has_completed_errors
        or sync_status == "completed_with_errors"
    ):
        return "needs_attention"
    return "ready"
