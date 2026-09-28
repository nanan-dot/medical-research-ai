"""AC-10—13：CSV 内容一致性与阻断校验。"""

import hashlib
import io

import pytest
from starlette.datastructures import UploadFile

from app.modules.literature_search.journal_metric_import import (
    JournalMetricImportError,
    parse_journal_metric_csv,
)

VALID = (
    b"journal_name,issn,metric_year,impact_factor\nExample Journal,2049-3630,2025,1.2\n"
)


@pytest.mark.asyncio
async def test_preview_is_read_only() -> None:
    parsed = await parse_journal_metric_csv(
        UploadFile(io.BytesIO(VALID), filename="metrics.csv"), 1024
    )
    assert parsed.preview.is_committable and parsed.preview.valid_rows == 1
    assert parsed.file_hash == hashlib.sha256(VALID).hexdigest()


@pytest.mark.asyncio
async def test_preview_rejects_invalid_input_without_writes() -> None:
    with pytest.raises(JournalMetricImportError) as caught:
        await parse_journal_metric_csv(
            UploadFile(io.BytesIO(b"name\nX\n"), filename="metrics.csv"), 1024
        )
    assert caught.value.code == "journal_metric_missing_headers"


@pytest.mark.asyncio
async def test_invalid_rows_make_file_non_committable() -> None:
    content = b"journal_name,metric_year,impact_factor\nExample Journal,2025,-1\n"
    parsed = await parse_journal_metric_csv(
        UploadFile(io.BytesIO(content), filename="metrics.csv"), 1024
    )
    assert not parsed.preview.is_committable and parsed.preview.error_rows == 1


@pytest.mark.asyncio
async def test_file_size_is_bounded() -> None:
    with pytest.raises(JournalMetricImportError) as caught:
        await parse_journal_metric_csv(
            UploadFile(io.BytesIO(VALID), filename="metrics.csv"), 10
        )
    assert caught.value.code == "journal_metric_file_too_large"
