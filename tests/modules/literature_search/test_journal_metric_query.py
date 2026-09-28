"""AC-19—23：字段独立年份、空值和 WoS 真实性。"""

from app.modules.literature_search.journal_metric_query import (
    history_item,
    summarize_metrics,
)
from app.modules.literature_search.model import LiteratureCommercialJournalMetric


def metric(year: int, **values: object) -> LiteratureCommercialJournalMetric:
    return LiteratureCommercialJournalMetric(
        journal_key="2049-3630",
        journal_name="Example Journal",
        normalized_journal_name="example journal",
        metric_year=year,
        provider="Example",
        provider_version=str(year),
        status="available",
        **values,
    )


def test_latest_fields_keep_independent_years() -> None:
    summary = summarize_metrics(
        [
            metric(2025, impact_factor=8.6, impact_factor_year=2025),
            metric(2024, cas_quartile="1区", cas_year=2024),
        ],
        "issn_exact",
    )
    assert summary.latest and summary.latest.impact_factor.year == 2025
    assert summary.latest.cas.year == 2024


def test_missing_if_stays_null() -> None:
    summary = summarize_metrics([metric(2025, jcr_best_quartile="Q1")], "issn_exact")
    assert summary.latest and summary.latest.impact_factor.value is None


def test_esci_is_not_promoted_to_scie() -> None:
    item = history_item(metric(2025, impact_factor=1.0, wos_indexes_json='["ESCI"]'))
    assert item.wos_indexes == ["ESCI"]


def test_history_model_preserves_exact_metric_year() -> None:
    assert history_item(metric(2014, impact_factor=1.0)).metric_year == 2014
