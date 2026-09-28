"""有界、可重复验证的 UTF-8 CSV 期刊指标解析。"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass

from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.common.exceptions import AppError
from app.modules.literature_search.journal_metric_normalization import normalize_issn
from app.modules.literature_search.journal_metric_schema import (
    JournalMetricImportPreview,
    JournalMetricRow,
)

REQUIRED_HEADERS = {"journal_name", "metric_year"}
ERROR_SAMPLE_LIMIT = 20
READ_CHUNK_BYTES = 1024 * 1024


class JournalMetricImportError(AppError):
    status_code = 422


@dataclass(frozen=True)
class ParsedJournalMetricCsv:
    filename: str
    file_hash: str
    rows: list[JournalMetricRow]
    preview: JournalMetricImportPreview


async def parse_journal_metric_csv(
    file: UploadFile, max_bytes: int
) -> ParsedJournalMetricCsv:
    """流式读取并哈希文件，在明确上限内解析全部行。"""
    filename = file.filename or "journal-metrics.csv"
    if not filename.casefold().endswith(".csv"):
        raise _error("journal_metric_invalid_rows", "only .csv files are accepted")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(READ_CHUNK_BYTES):
        size += len(chunk)
        if size > max_bytes:
            raise _error(
                "journal_metric_file_too_large",
                "journal metric CSV exceeds configured limit",
            )
        digest.update(chunk)
        chunks.append(chunk)
    try:
        text = b"".join(chunks).decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise _error(
            "journal_metric_invalid_encoding", "journal metric CSV must be UTF-8"
        ) from error
    return _parse_text(filename, digest.hexdigest(), text)


def _parse_text(filename: str, file_hash: str, text: str) -> ParsedJournalMetricCsv:
    reader = csv.DictReader(io.StringIO(text))
    headers = {header.strip() for header in (reader.fieldnames or []) if header}
    if not REQUIRED_HEADERS.issubset(headers):
        raise _error(
            "journal_metric_missing_headers",
            "journal_name and metric_year headers are required",
        )
    rows: list[JournalMetricRow] = []
    errors: list[str] = []
    duplicate_rows = 0
    seen_keys: set[tuple[str, str, str, str, int]] = set()
    total_rows = 0
    for line_number, raw in enumerate(reader, start=2):
        total_rows += 1
        try:
            row = _validate_row(raw)
            key = (
                row.journal_name.casefold(),
                row.issn or "",
                row.eissn or "",
                row.issn_l or "",
                row.metric_year,
            )
            if key in seen_keys:
                duplicate_rows += 1
                raise ValueError("duplicate journal identity in file")
            seen_keys.add(key)
            rows.append(row)
        except (ValueError, ValidationError) as error:
            if len(errors) < ERROR_SAMPLE_LIMIT:
                errors.append(f"row {line_number}: {error}")
    preview = JournalMetricImportPreview(
        total_rows=total_rows,
        valid_rows=len(rows),
        error_rows=total_rows - len(rows),
        duplicate_rows=duplicate_rows,
        error_samples=errors,
        file_hash=file_hash,
        is_committable=total_rows > 0 and len(rows) == total_rows,
    )
    return ParsedJournalMetricCsv(
        filename=filename, file_hash=file_hash, rows=rows, preview=preview
    )


def _validate_row(raw: dict[str, str | None]) -> JournalMetricRow:
    def value(name: str) -> str | None:
        candidate = (raw.get(name) or "").strip()
        return candidate or None

    wos = [
        part.strip().upper()
        for part in re.split(r"[,;]", value("wos_indexes") or "")
        if part.strip()
    ]
    payload: dict[str, object] = {
        "journal_name": value("journal_name"),
        "metric_year": value("metric_year"),
        "issn": normalize_issn(value("issn")),
        "eissn": normalize_issn(value("eissn")),
        "issn_l": normalize_issn(value("issn_l")),
        "impact_factor": value("impact_factor"),
        "impact_factor_year": value("impact_factor_year"),
        "jcr_best_quartile": (value("jcr_best_quartile") or "").upper() or None,
        "jcr_year": value("jcr_year"),
        "wos_indexes": wos,
        "wos_year": value("wos_year"),
        "cas_quartile": value("cas_quartile"),
        "cas_year": value("cas_year"),
        "cas_category": value("cas_category"),
        "warning_status": value("warning_status"),
    }
    top = value("is_cas_top")
    if top is not None:
        lowered = top.casefold()
        if lowered not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("is_cas_top must be a boolean")
        payload["is_cas_top"] = lowered in {"true", "1", "yes"}
    row = JournalMetricRow.model_validate(payload)
    if not any((row.issn, row.eissn, row.issn_l, row.journal_name)):
        raise ValueError("at least one journal identity is required")
    if not any(
        (
            row.impact_factor is not None,
            row.jcr_best_quartile,
            row.wos_indexes,
            row.cas_quartile,
        )
    ):
        raise ValueError("at least one metric field is required")
    return row


def _error(code: str, message: str) -> JournalMetricImportError:
    error = JournalMetricImportError(message)
    error.code = code
    return error
