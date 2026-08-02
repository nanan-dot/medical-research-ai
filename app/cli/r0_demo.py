"""R0 end-to-end PaperQA demo orchestration and CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.integrations.paperqa2 import PaperDocument, PaperQAAnswer
from app.integrations.paperqa2.exceptions import PaperQA2Error
from app.integrations.paperqa2.factory import create_paperqa2_client


class DemoError(Exception):
    def __init__(self, message: str, *, exit_code: int):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class DemoTimings(BaseModel):
    index_seconds: float = Field(ge=0)
    ask_seconds: float = Field(ge=0)
    total_seconds: float = Field(ge=0)


class DemoResult(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    provider: Literal["ollama", "openai", "openrouter"]
    model: str
    document: str
    question: str
    rebuild_requested: bool
    index_reused: bool
    answer: PaperQAAnswer
    timings: DemoTimings


class PaperQAClientProtocol(Protocol):
    async def index_documents(self, documents, *, rebuild: bool = False): ...

    async def ask(self, index, question): ...


async def run_demo(
    *,
    client: PaperQAClientProtocol,
    pdf_path: Path,
    question: str,
    provider: Literal["ollama", "openai", "openrouter"],
    model: str,
    output_path: Path,
    rebuild: bool = False,
    max_reuse_seconds: float = 5.0,
) -> DemoResult:
    pdf_path = _validate_pdf(pdf_path)
    question = question.strip()
    if not question:
        raise DemoError("Question must not be empty", exit_code=2)

    total_started = perf_counter()
    index_started = perf_counter()
    index = await client.index_documents([PaperDocument(path=pdf_path)], rebuild=rebuild)
    index_seconds = perf_counter() - index_started
    if index.reused and index_seconds > max_reuse_seconds:
        raise DemoError(
            f"Reused index exceeded {max_reuse_seconds:.1f} seconds",
            exit_code=1,
        )

    ask_started = perf_counter()
    answer = await client.ask(index, question)
    ask_seconds = perf_counter() - ask_started
    if not answer.answer.strip():
        raise DemoError("PaperQA2 returned an empty answer", exit_code=1)

    result = DemoResult(
        provider=provider,
        model=model,
        document=pdf_path.name,
        question=question,
        rebuild_requested=rebuild,
        index_reused=index.reused,
        answer=answer,
        timings=DemoTimings(
            index_seconds=index_seconds,
            ask_seconds=ask_seconds,
            total_seconds=perf_counter() - total_started,
        ),
    )
    _write_json(output_path, result)
    return result


def _validate_pdf(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise DemoError(f"PDF does not exist: {path}", exit_code=2)
    if path.suffix.lower() != ".pdf":
        raise DemoError("Input document must have a .pdf extension", exit_code=2)
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise DemoError("Input document is not a valid PDF", exit_code=2)
    return path


def _write_json(path: Path, result: DemoResult) -> None:
    try:
        path = path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as error:
        raise DemoError("Demo output path is not writable", exit_code=3) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True, help="Path to a text PDF")
    parser.add_argument("--question", required=True, help="Factual question for the PDF")
    parser.add_argument(
        "--provider",
        choices=("ollama", "openai", "openrouter"),
        default="ollama",
    )
    parser.add_argument("--model", help="Override the provider model from .env")
    parser.add_argument("--base-url", help="Override the provider base URL from .env")
    parser.add_argument("--output", type=Path, required=True, help="Result JSON path")
    parser.add_argument("--rebuild", action="store_true", help="Request a fresh process index")
    parser.add_argument("--max-reuse-seconds", type=float, default=5.0)
    return parser


def _settings_for_args(args: argparse.Namespace) -> tuple[Settings, str]:
    app_settings = Settings()
    provider = args.provider
    model_field = f"{provider.upper()}_MODEL"
    base_field = f"{provider.upper()}_BASE_URL"
    updates = {}
    if args.model:
        updates[model_field] = args.model
    if args.base_url:
        updates[base_field] = args.base_url
    if updates:
        app_settings = app_settings.model_copy(update=updates)
    model = getattr(app_settings, model_field)
    if not model:
        raise DemoError(f"Model is not configured for provider '{provider}'", exit_code=2)
    return app_settings, model


async def _async_main(args: argparse.Namespace) -> DemoResult:
    app_settings, model = _settings_for_args(args)
    client = create_paperqa2_client(app_settings, provider=args.provider)
    return await run_demo(
        client=client,
        pdf_path=args.pdf,
        question=args.question,
        provider=args.provider,
        model=model,
        output_path=args.output,
        rebuild=args.rebuild,
        max_reuse_seconds=args.max_reuse_seconds,
    )


def print_result(result: DemoResult) -> None:
    print(f"provider={result.provider}")
    print(f"model={result.model}")
    print(f"index_reused={str(result.index_reused).lower()}")
    print(f"index_seconds={result.timings.index_seconds:.3f}")
    print(f"ask_seconds={result.timings.ask_seconds:.3f}")
    print("answer:")
    print(_console_safe(result.answer.answer))
    print("sources:")
    for position, source in enumerate(result.answer.sources, start=1):
        pages = (
            f"{source.page_start}-{source.page_end}" if source.page_start is not None else "unknown"
        )
        print(f"{position}. {source.citation or source.title or 'unknown'}; pages={pages}")


def _console_safe(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="backslashreplace").decode(encoding)


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        result = asyncio.run(_async_main(args))
        print_result(result)
        return 0
    except DemoError as error:
        print(f"R0 demo failed: {error.message}", file=sys.stderr)
        return error.exit_code
    except PaperQA2Error as error:
        print(f"R0 demo failed [{error.code}]: {error.message}", file=sys.stderr)
        return 1
