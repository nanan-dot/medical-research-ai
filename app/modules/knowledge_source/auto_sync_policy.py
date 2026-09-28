"""自动同步时间策略；不包含数据库或调度副作用。"""

from datetime import datetime, timedelta

MIN_SYNC_INTERVAL_MINUTES = 5
MAX_SYNC_INTERVAL_MINUTES = 24 * 60
MAX_AUTO_SYNC_BACKOFF_MINUTES = 24 * 60


def validate_sync_interval_minutes(interval_minutes: int) -> int:
    """校验间隔，防止忙循环和失去及时性。"""
    if not MIN_SYNC_INTERVAL_MINUTES <= interval_minutes <= MAX_SYNC_INTERVAL_MINUTES:
        raise ValueError("sync_interval_minutes is outside the supported range")
    return interval_minutes


def next_auto_sync_at(
    now: datetime, interval_minutes: int, failure_count: int = 0
) -> datetime:
    """计算下次时间；失败采用有上界的指数退避。"""
    interval = validate_sync_interval_minutes(interval_minutes)
    delay_minutes = min(
        interval * (2 ** min(max(failure_count, 0), 8)),
        MAX_AUTO_SYNC_BACKOFF_MINUTES,
    )
    return now + timedelta(minutes=delay_minutes)
