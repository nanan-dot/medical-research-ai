"""Adapter boundary for licensed journal/database metrics.

No provider is bundled: callers must supply an authorized source and its
license provenance. OpenAlex article citations deliberately do not implement
this protocol.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

CommercialMetricStatus = Literal["available", "not_configured", "not_found", "ambiguous", "unavailable"]


@dataclass(frozen=True)
class CommercialJournalMetric:
    journal_key: str
    provider: str | None
    provider_version: str | None
    license_provenance: str | None
    metric_year: int | None
    impact_factor: float | None
    impact_factor_year: int | None
    jcr_best_quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None
    jcr_year: int | None
    wos_indexes: tuple[Literal["SCIE", "SSCI", "ESCI", "AHCI"], ...]
    wos_year: int | None
    cas_quartile: Literal["1区", "2区", "3区", "4区"] | None
    cas_year: int | None
    status: CommercialMetricStatus
    reason: str | None
    observed_at: datetime | None


class CommercialMetricsProvider(Protocol):
    """An adapter backed by a user-authorized provider or licensed import."""

    async def lookup(
        self, journal_key: str, metric_year: int | None = None
    ) -> CommercialJournalMetric: ...


class UnconfiguredCommercialMetricsProvider:
    """Truthful default when the deployment has no licensed metric source."""

    async def lookup(
        self, journal_key: str, metric_year: int | None = None
    ) -> CommercialJournalMetric:
        return CommercialJournalMetric(
            journal_key=journal_key,
            provider=None,
            provider_version=None,
            license_provenance=None,
            metric_year=metric_year,
            impact_factor=None,
            impact_factor_year=None,
            jcr_best_quartile=None,
            jcr_year=None,
            wos_indexes=(),
            wos_year=None,
            cas_quartile=None,
            cas_year=None,
            status="not_configured",
            reason="no_licensed_commercial_metrics_provider_configured",
            observed_at=None,
        )
