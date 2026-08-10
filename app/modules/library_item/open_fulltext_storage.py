"""Controlled filesystem persistence for a verified PMC PDF."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from app.core.config import settings
from app.modules.library_item.official_pmc_client import (
    OfficialPmcError,
    OfficialPmcGateway,
)

_DOCUMENTS_DIRECTORY = "documents"
_TEMPORARY_DIRECTORY = ".tmp"


@dataclass(frozen=True)
class StoredOpenFulltextPdf:
    absolute_path: Path
    relative_path: str
    byte_size: int
    sha256: str
    modified_time: datetime
    modified_time_ns: int


class OpenFulltextStorage:
    """The caller never supplies a destination path; only a vetted PMC URL reaches disk."""

    async def store(
        self, gateway: OfficialPmcGateway, pmcid: str, pdf_url: str
    ) -> StoredOpenFulltextPdf:
        root, temporary_directory, documents_directory = await asyncio.to_thread(
            _prepare_directories
        )
        temporary_path = temporary_directory / f"{uuid4().hex}.downloading"
        final_path = documents_directory / f"{uuid4().hex}.pdf"
        try:
            downloaded = await gateway.download_pdf_to_path(
                pdf_url, temporary_path, settings.MAX_OPEN_FULLTEXT_PDF_BYTES
            )
            await asyncio.to_thread(_validate_pdf, temporary_path)
            await asyncio.to_thread(os.replace, temporary_path, final_path)
            stat = await asyncio.to_thread(final_path.stat)
            return StoredOpenFulltextPdf(
                absolute_path=final_path,
                relative_path=final_path.relative_to(root).as_posix(),
                byte_size=downloaded.byte_size,
                sha256=downloaded.sha256,
                modified_time=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                modified_time_ns=stat.st_mtime_ns,
            )
        except OfficialPmcError:
            await asyncio.to_thread(_remove_if_exists, temporary_path)
            await asyncio.to_thread(_remove_if_exists, final_path)
            raise
        except OSError as exc:
            await asyncio.to_thread(_remove_if_exists, temporary_path)
            await asyncio.to_thread(_remove_if_exists, final_path)
            raise OfficialPmcError("storage_failed", "无法保存 PMC 官方 PDF") from exc
        except Exception:
            await asyncio.to_thread(_remove_if_exists, temporary_path)
            await asyncio.to_thread(_remove_if_exists, final_path)
            raise


def _prepare_directories() -> tuple[Path, Path, Path]:
    root = settings.OPEN_FULLTEXT_DIR.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    temporary_directory = _safe_descendant(resolved_root, resolved_root / _TEMPORARY_DIRECTORY)
    documents_directory = _safe_descendant(resolved_root, resolved_root / _DOCUMENTS_DIRECTORY)
    temporary_directory.mkdir(exist_ok=True)
    documents_directory.mkdir(exist_ok=True)
    return (
        resolved_root,
        temporary_directory.resolve(strict=True),
        documents_directory.resolve(strict=True),
    )


def _safe_descendant(root: Path, candidate: Path) -> Path:
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(root)
    except ValueError as exc:
        raise OfficialPmcError("storage_failed", "PMC 全文存储路径越界") from exc
    return resolved_candidate


def _validate_pdf(path: Path) -> None:
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted or len(reader.pages) == 0:
            raise ValueError("unsupported PDF")
    except Exception as exc:
        raise OfficialPmcError("content_invalid", "PMC 下载文件不是可读取的未加密 PDF") from exc


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
