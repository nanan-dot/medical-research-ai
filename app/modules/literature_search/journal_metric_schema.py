"""期刊指标导入、摘要与详情 API 契约。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

WosIndex = Literal["SCIE", "SSCI", "ESCI", "AHCI"]
BatchStatus = Literal["ready", "active", "archived", "failed"]


class JournalMetricRow(BaseModel):
    journal_name: str = Field(min_length=1, max_length=500)
    issn: str | None = Field(default=None, max_length=9)
    eissn: str | None = Field(default=None, max_length=9)
    issn_l: str | None = Field(default=None, max_length=9)
    metric_year: int = Field(ge=1900, le=2200)
    impact_factor: float | None = Field(default=None, ge=0)
    impact_factor_year: int | None = Field(default=None, ge=1900, le=2200)
    jcr_best_quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None = None
    jcr_year: int | None = Field(default=None, ge=1900, le=2200)
    wos_indexes: list[WosIndex] = Field(default_factory=list)
    wos_year: int | None = Field(default=None, ge=1900, le=2200)
    cas_quartile: Literal["1区", "2区", "3区", "4区"] | None = None
    cas_year: int | None = Field(default=None, ge=1900, le=2200)
    cas_category: str | None = Field(default=None, max_length=200)
    is_cas_top: bool | None = None
    warning_status: str | None = Field(default=None, max_length=100)

    @field_validator("wos_indexes")
    @classmethod
    def unique_wos_indexes(cls, values: list[WosIndex]) -> list[WosIndex]:
        return list(dict.fromkeys(values))


class JournalMetricImportPreview(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_rows: int
    error_samples: list[str] = Field(default_factory=list)
    file_hash: str = Field(min_length=64, max_length=64)
    is_committable: bool


class JournalMetricImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    edition_year: int
    provider: str
    provider_version: str
    source_filename: str
    source_file_hash: str
    license_provenance: str
    record_count: int
    status: BatchStatus
    is_active: bool
    error_summary: str | None = None
    created_at: datetime
    activated_at: datetime | None = None


class JournalMetricImportBatchList(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[JournalMetricImportBatchRead]


class MetricValue(BaseModel):
    value: float | None
    year: int | None


class JcrValue(BaseModel):
    best_quartile: str | None
    year: int | None


class WosValue(BaseModel):
    indexes: list[WosIndex] | None
    year: int | None


class CasValue(BaseModel):
    quartile: str | None
    year: int | None
    category: str | None = None
    is_top: bool | None = None


class JournalMetricLatest(BaseModel):
    impact_factor: MetricValue
    jcr: JcrValue
    wos: WosValue
    cas: CasValue


class JournalMetricSummary(BaseModel):
    status: Literal[
        "matched", "not_found", "ambiguous", "not_configured", "unavailable"
    ]
    match_method: (
        Literal["issn_l_exact", "issn_exact", "eissn_exact", "normalized_title_exact"]
        | None
    ) = None
    latest: JournalMetricLatest | None = None
    reason: str | None = None


class JournalMetricHistoryItem(JournalMetricRow):
    provider: str
    provider_version: str


class JournalMetricDetail(BaseModel):
    summary: JournalMetricSummary
    publication_year_metric: JournalMetricHistoryItem | None = None
    publication_year_reason: str | None = None
    history: list[JournalMetricHistoryItem] = Field(default_factory=list, max_length=10)
