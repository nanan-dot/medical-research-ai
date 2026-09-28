"""论文库 V3.1 的分析进度与工作入口纯投影验收。"""

from datetime import UTC, datetime, timedelta

from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.analysis_progress import (
    encode_task_names,
    project_analysis_progress,
)
from app.modules.paper_library.model import PaperWorkState
from app.modules.paper_library.service import PaperLibraryService
from app.modules.paper_library.work_projection import project_work_entries


def analysis(*, status: str, tasks: tuple[str, ...] | None, completed: tuple[str, ...] = ()):
    now = datetime.now(UTC)
    return PaperAnalysis(
        document_id=1,
        analysis_status=status,
        template_version="general-v2",
        model_version="test",
        generation=1,
        task_set_version="general-v2" if tasks is not None else None,
        task_names_json=encode_task_names(tasks) if tasks is not None else None,
        completed_task_names_json=(
            encode_task_names(completed) if tasks is not None else None
        ),
        created_at=now,
        updated_at=now,
    )


def test_analysis_progress_uses_persisted_task_set_size_for_all_statuses():
    partial = analysis(status="analyzing", tasks=("a", "b", "c"), completed=("a",))
    failed = analysis(status="failed", tasks=("a", "b"), completed=("a",))
    cancelled = analysis(status="cancelled", tasks=("a", "b", "c", "d"), completed=("a", "b"))

    assert project_analysis_progress(partial).completed == 1
    assert PaperLibraryService._analysis_projection(partial) == (
        "analyzing",
        {"completed": 1, "total": 3},
    )
    assert PaperLibraryService._analysis_projection(failed)[1] == {"completed": 1, "total": 2}
    assert PaperLibraryService._analysis_projection(cancelled) == (
        "cancelled",
        {"completed": 2, "total": 4},
    )


def test_unknown_historical_and_zero_task_progress_are_not_fabricated():
    historical = analysis(status="succeeded", tasks=None)
    zero_tasks = analysis(status="succeeded", tasks=())

    assert PaperLibraryService._analysis_projection(historical) == ("completed", None)
    assert PaperLibraryService._analysis_projection(zero_tasks) == ("completed", None)


def test_work_projection_prefers_latest_real_work_event():
    now = datetime.now(UTC)
    state = PaperWorkState(
        library_item_id=1,
        reading_status="reading",
        reading_progress_percent=30,
        last_read_at=now - timedelta(minutes=5),
        last_analysis_at=now,
        last_work_kind="analysis",
    )
    projected = project_work_entries(
        state,
        analysis_status="analyzing",
        can_read=True,
        can_analyze=True,
        reading_reason=None,
        analysis_reason=None,
    )

    assert projected.preferred_action == "analysis"
    assert projected.last_work_at == now
    assert projected.analysis.action == "continue"
