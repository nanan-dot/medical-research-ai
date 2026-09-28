"""同步进度的真实工作量计算行为测试。"""

from app.modules.knowledge_source.sync_progress import (
    SyncPhase,
    calculate_progress,
    completed_progress,
)


def test_scanning_progress_is_indeterminate_until_file_count_is_known() -> None:
    """AC-PROGRESS-01：目录扫描前不得猜测百分比。"""
    progress = calculate_progress(SyncPhase.SCANNING, 0, None)
    assert progress.total_units is None
    assert progress.progress_percent is None


def test_running_progress_is_monotonic_and_never_reaches_100() -> None:
    """AC-PROGRESS-02/03：运行中由单位计算且完成前最大为 99。"""
    values = [
        calculate_progress(SyncPhase.HASHING, completed, 10).progress_percent
        for completed in range(11)
    ]
    assert values == sorted(values)
    assert values[-1] == 99
    assert completed_progress().progress_percent == 100
