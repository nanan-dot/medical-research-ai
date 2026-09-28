"""受控进程边界：逐页校验、磁盘暂存、总/空闲超时与进程树回收。"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import signal
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile

from app.common.exceptions import TemporarilyUnavailableError
from app.core.config import settings
from app.modules.document_anchor.contract import (
    ContractValidationError,
    TrailerRecord,
    validate_header,
    validate_page,
)
from app.modules.document_anchor.fingerprint import document_content_hash
from app.modules.document_anchor.input_validation import verify_pdf
from app.modules.document_anchor.quality import page_quality
from app.modules.document_anchor.staging import StagedExtraction, StagedPages
from app.modules.document_anchor.toolchain import (
    CONTRACT_SCHEMA_VERSION,
    RESULT_OPTIONS,
    identity,
)

Progress = Callable[[int, int], Awaitable[None]]
EXIT_CODES = {
    2: "invalid_argument",
    3: "file_hash_mismatch",
    4: "invalid_pdf",
    5: "encrypted_pdf",
    6: "resource_limit_exceeded",
    7: "extraction_failed",
    8: "contract_write_failed",
}


class ExtractorUnavailableError(TemporarilyUnavailableError):
    code = "anchor_extractor_unavailable"


class ExtractorExecutionError(RuntimeError):
    def __init__(self, code: str = "anchor_extraction_failed") -> None:
        self.code = code
        super().__init__(code)


def extractor_command() -> tuple[str, ...]:
    """Accept a JSON argv array, retaining quoted legacy commands without a shell."""
    raw = settings.PDF_TEXTITEM_EXTRACTOR_COMMAND.strip()
    try:
        values = (
            json.loads(raw)
            if raw.startswith("[")
            else [value.strip('"') for value in shlex.split(raw, posix=os.name != "nt")]
        )
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(value, str) and value for value in values)
        ):
            raise ValueError("Invalid command")
        return tuple(values)
    except (ValueError, TypeError) as exc:
        raise ExtractorUnavailableError(
            "PDF TextItem extractor is not configured correctly"
        ) from exc


async def stop_process_tree(process: asyncio.subprocess.Process) -> None:
    """Reap the owned process tree, including Windows child processes."""
    job = getattr(process, "anchor_job", None)
    if job is not None:
        job.close()
    if os.name == "nt" and process.returncode is None:
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        await killer.wait()
    elif os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]  # POSIX 分支，Windows stubs 无此属性。
        except ProcessLookupError:
            pass  # 已退出的进程组无需再次终止。
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass  # taskkill 与回收可能恰好同时完成。
    await process.wait()


async def _spawn(*arguments: str) -> asyncio.subprocess.Process:
    try:
        process = await asyncio.create_subprocess_exec(
            *extractor_command(),
            *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=settings.PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES + 1,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if os.name == "nt":
            from app.modules.document_anchor.windows_job import WindowsJob

            try:
                process.anchor_job = WindowsJob(process.pid)  # type: ignore[attr-defined]  # 由 runner 持有的生命周期资源。
            except OSError:
                await stop_process_tree(process)
                raise
        return process
    except OSError as exc:
        raise ExtractorUnavailableError(
            "PDF TextItem extractor cannot be started"
        ) from exc


class PdfTextItemExtractor:
    def __init__(self, progress: Progress | None = None) -> None:
        self.progress = progress

    async def probe(self) -> dict[str, str]:
        """Check executable/package compatibility without parsing a document."""
        process = await _spawn("--version-json")
        try:
            if process.stdout is None:
                raise ValueError("Missing stdout")
            async with asyncio.timeout(10):
                output = await process.stdout.read(4097)
                await process.wait()
            if (
                process.returncode
                or len(output) > 4096
                or json.loads(output) != identity()
            ):
                raise ValueError("Incompatible extractor")
            return identity()
        except (ValueError, TimeoutError) as exc:
            raise ExtractorUnavailableError(
                "PDF TextItem extractor is unavailable or incompatible"
            ) from exc
        finally:
            await stop_process_tree(process)

    async def extract(
        self, path: Path, expected_sha256: str, request_id: str
    ) -> StagedExtraction:
        await asyncio.to_thread(verify_pdf, path, expected_sha256)
        options_path = await asyncio.to_thread(self._write_options_file)
        process = None
        try:
            process = await _spawn(
                "extract",
                "--input",
                str(path),
                "--expected-sha256",
                expected_sha256,
                "--request-id",
                request_id,
                "--options-file",
                str(options_path),
            )
            async with asyncio.timeout(settings.PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS):
                stream = await self._read_records(process, request_id, expected_sha256)
            try:
                await asyncio.to_thread(verify_pdf, path, expected_sha256)
            except BaseException:
                stream.close()
                raise
            return stream
        except TimeoutError as exc:
            raise ExtractorExecutionError("anchor_extraction_timeout") from exc
        finally:
            if process is not None:
                await stop_process_tree(process)
            await asyncio.to_thread(options_path.unlink, missing_ok=True)

    async def _read_records(
        self, process: asyncio.subprocess.Process, request_id: str, file_hash: str
    ) -> StagedExtraction:
        if process.stdout is None:
            raise ExtractorExecutionError("anchor_missing_stdout")
        staged = TemporaryFile(  # noqa: SIM115 -- 所有权移交 StagedExtraction，发布后关闭。
            mode="w+", encoding="utf-8", dir=settings.DATA_DIR / "anchor_extractor"
        )
        offsets: list[int] = []
        hashes: list[str] = []
        flags: list[list[str]] = []
        header = None
        trailer = None
        output_bytes, items = 0, 0
        try:
            while True:
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        settings.PDF_TEXTITEM_EXTRACTOR_IDLE_TIMEOUT_SECONDS,
                    )
                except TimeoutError as exc:
                    raise ExtractorExecutionError(
                        "anchor_extraction_idle_timeout"
                    ) from exc
                if not line:
                    break
                output_bytes += len(line)
                if (
                    len(line) > settings.PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES
                    or output_bytes > settings.PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES
                ):
                    raise ExtractorExecutionError("resource_limit_exceeded")
                record = json.loads(line)
                if not isinstance(record, dict) or trailer is not None:
                    raise ContractValidationError("Unexpected extractor record")
                if header is None:
                    header = validate_header(record, request_id, file_hash)
                    if header.page_count > settings.PDF_TEXTITEM_EXTRACTOR_MAX_PAGES:
                        raise ExtractorExecutionError("resource_limit_exceeded")
                    if self.progress:
                        await self.progress(0, header.page_count)
                elif record.get("record_type") == "trailer":
                    trailer = TrailerRecord.model_validate(record)
                else:
                    if len(offsets) >= header.page_count:
                        raise ContractValidationError("Extra extractor page")
                    page = validate_page(record, len(offsets) + 1)
                    if (
                        len(page.items)
                        > settings.PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE
                    ):
                        raise ExtractorExecutionError("resource_limit_exceeded")
                    offsets.append(staged.tell())
                    staged.write(page.model_dump_json() + "\n")
                    staged.flush()
                    hashes.append(page.page_content_hash)
                    flags.append(page_quality(page)[1])
                    items += len(page.items)
                    if self.progress:
                        await self.progress(len(offsets), header.page_count)
            await process.wait()
            if process.returncode:
                raise ExtractorExecutionError(
                    EXIT_CODES.get(process.returncode, "anchor_process_failed")
                )
            content_hash = document_content_hash(hashes)
            if (
                header is None
                or trailer is None
                or not trailer.completed
                or trailer.request_id != request_id
                or header.page_count != len(offsets)
                or trailer.pages_emitted != len(offsets)
                or trailer.items_emitted != items
                or trailer.document_content_hash != content_hash
            ):
                raise ContractValidationError("Incomplete extractor stream")
            return StagedExtraction(
                header,
                StagedPages(staged, offsets),
                trailer,
                hashes,
                content_hash,
                flags,
            )
        except BaseException as exc:
            staged.close()
            if isinstance(exc, (ValueError, UnicodeError)):
                raise ExtractorExecutionError("anchor_invalid_contract") from exc
            raise

    @staticmethod
    def _write_options_file() -> Path:
        options = {
            **RESULT_OPTIONS,
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "max_pages": settings.PDF_TEXTITEM_EXTRACTOR_MAX_PAGES,
            "max_items_per_page": settings.PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE,
            "max_item_characters": 20_000,
            "max_file_bytes": settings.PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES,
            "max_line_bytes": settings.PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES,
            "max_output_bytes": settings.PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES,
        }
        directory = settings.DATA_DIR / "anchor_extractor"
        directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix="options-",
            suffix=".json",
            delete=False,
        ) as file:
            file.write(json.dumps(options))
            return Path(file.name)
