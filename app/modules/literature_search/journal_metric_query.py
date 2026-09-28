"""期刊指标摘要与历史的纯选择逻辑。"""

from __future__ import annotations

import json
from typing import Literal, cast

from app.modules.literature_search.journal_metric_matching import MatchMethod
from app.modules.literature_search.journal_metric_schema import (
    CasValue,
    JcrValue,
    JournalMetricHistoryItem,
    JournalMetricLatest,
    JournalMetricSummary,
    MetricValue,
    WosValue,
)
from app.modules.literature_search.model import LiteratureCommercialJournalMetric


def summarize_metrics(
    metrics: list[LiteratureCommercialJournalMetric], match_method: str
) -> JournalMetricSummary:
    """逐字段选取最新非空值，并保留各自年度。"""
    ordered = sorted(metrics, key=lambda metric: metric.metric_year or 0, reverse=True)
    impact = next(
        (metric for metric in ordered if metric.impact_factor is not None), None
    )
    jcr = next(
        (metric for metric in ordered if metric.jcr_best_quartile is not None), None
    )
    wos = next((metric for metric in ordered if metric.wos_indexes_json), None)
    cas = next((metric for metric in ordered if metric.cas_quartile is not None), None)
    return JournalMetricSummary(
        status="matched",
        match_method=cast(MatchMethod, match_method),
        latest=JournalMetricLatest(
            impact_factor=MetricValue(
                value=impact.impact_factor if impact else None,
                year=(impact.impact_factor_year or impact.metric_year)
                if impact
                else None,
            ),
            jcr=JcrValue(
                best_quartile=jcr.jcr_best_quartile if jcr else None,
                year=(jcr.jcr_year or jcr.metric_year) if jcr else None,
            ),
            wos=WosValue(
                indexes=json.loads(wos.wos_indexes_json)
                if wos and wos.wos_indexes_json
                else None,
                year=(wos.wos_year or wos.metric_year) if wos else None,
            ),
            cas=CasValue(
                quartile=cas.cas_quartile if cas else None,
                year=(cas.cas_year or cas.metric_year) if cas else None,
                category=cas.cas_category if cas else None,
                is_top=cas.is_cas_top if cas else None,
            ),
        ),
    )


def history_item(metric: LiteratureCommercialJournalMetric) -> JournalMetricHistoryItem:
    return JournalMetricHistoryItem(
        journal_name=metric.journal_name or metric.journal_key,
        issn=metric.issn,
        eissn=metric.eissn,
        issn_l=metric.issn_l,
        metric_year=metric.metric_year or 1900,
        impact_factor=metric.impact_factor,
        impact_factor_year=metric.impact_factor_year,
        jcr_best_quartile=cast(
            Literal["Q1", "Q2", "Q3", "Q4"] | None,
            metric.jcr_best_quartile,
        ),
        jcr_year=metric.jcr_year,
        wos_indexes=json.loads(metric.wos_indexes_json or "[]"),
        wos_year=metric.wos_year,
        cas_quartile=cast(
            Literal["1区", "2区", "3区", "4区"] | None,
            metric.cas_quartile,
        ),
        cas_year=metric.cas_year,
        cas_category=metric.cas_category,
        is_cas_top=metric.is_cas_top,
        warning_status=metric.warning_status,
        provider=metric.provider or "unknown",
        provider_version=metric.provider_version or "unknown",
    )
