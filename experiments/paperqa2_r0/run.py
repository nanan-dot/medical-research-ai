"""Independent PaperQA2 experiment backed only by a local Ollama server."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import pickle
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PAPERQA_VERSION = "2026.3.18"
DEFAULT_QUESTION = (
    "How many cumulative first microvascular and macrovascular events occurred during "
    "6.5 years of observation, and how many were in the intervention and usual-care groups?"
)
PAPER_TITLE = (
    "Effect of a multicomponent quality improvement strategy on sustained "
    "achievement of diabetes care goals and macrovascular and microvascular "
    "complications in South Asia at 6.5 years follow-up: Post hoc analyses "
    "of the CARRS randomized clinical trial"
)
PAPER_CITATION = f"{PAPER_TITLE}. PLOS Medicine (2023). doi:10.1371/journal.pmed.1004335"
PUBLIC_SOURCE_URL = (
    "https://journals.plos.org/plosmedicine/article/file?"
    "id=10.1371%2Fjournal.pmed.1004335&type=printable"
)


class ExperimentInputError(ValueError):
    """Raised when an experiment input violates its local trust boundary."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pdf(path: Path) -> Path:
    path = path.resolve()
    if not path.is_file():
        raise ExperimentInputError(f"PDF does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ExperimentInputError(f"Input must use a .pdf extension: {path}")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ExperimentInputError(f"Input is not a PDF file: {path}")
    return path


def ensure_within(path: Path, root: Path, label: str) -> Path:
    resolved, resolved_root = path.resolve(), root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ExperimentInputError(f"{label} must remain under {resolved_root}")
    return resolved


def save_trusted_index(path: Path, root: Path, docs: Any, metadata: dict[str, str]) -> None:
    path = ensure_within(path, root, "Index")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        pickle.dump({"metadata": metadata, "docs": docs}, stream)
    temporary.replace(path)


def load_trusted_index(path: Path, root: Path, expected: dict[str, str]) -> Any:
    path = ensure_within(path, root, "Index")
    with path.open("rb") as stream:
        payload = pickle.load(stream)  # noqa: S301 - restricted to this experiment's data root
    if not isinstance(payload, dict) or payload.get("metadata") != expected:
        raise ExperimentInputError("Index metadata does not match PDF or PaperQA version")
    return payload["docs"]


def _clean_excerpt(value: str, limit: int = 600) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit]


def sanitize_session(
    session: Any,
    *,
    run_metadata: dict[str, Any],
    index_metadata: dict[str, Any],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    used_contexts = set(getattr(session, "used_contexts", []) or [])
    for position, context in enumerate(getattr(session, "contexts", []) or [], start=1):
        text = getattr(context, "text", None)
        document = getattr(text, "doc", None)
        chunk_name = str(getattr(text, "name", ""))
        page_match = re.search(r"\bpages?\s+(\d+(?:-\d+)?)", chunk_name, re.I)
        body = str(getattr(context, "context", "") or getattr(text, "text", ""))
        sources.append(
            {
                "rank": position,
                "title": str(getattr(document, "title", "") or run_metadata.get("paper_title", "")),
                "citation": str(getattr(document, "citation", "")),
                "chunk_name": chunk_name,
                "page_range": page_match.group(1) if page_match else None,
                "score": getattr(context, "score", None),
                "used_in_answer": position - 1 in used_contexts,
                "evidence_excerpt": _clean_excerpt(body),
            }
        )

    answer = str(getattr(session, "answer", "") or "")
    raw_answer = str(getattr(session, "raw_answer", "") or "")
    combined = answer + raw_answer
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "run": run_metadata,
        "index": index_metadata,
        "question": str(getattr(session, "question", DEFAULT_QUESTION)),
        "answer": answer,
        "raw_answer": raw_answer,
        "answer_reasoning": str(getattr(session, "answer_reasoning", "") or ""),
        "formatted_answer": str(getattr(session, "formatted_answer", "") or ""),
        "has_successful_answer": bool(getattr(session, "has_successful_answer", False)),
        "sources": sources,
        "capabilities": {
            "nonempty_answer": bool(answer.strip() or raw_answer.strip()),
            "source_count": len(sources),
            "paper_title_present": any(source["title"] for source in sources),
            "page_range_present": any(source["page_range"] for source in sources),
            "expected_values_present": all(value in combined for value in ("507", "233", "274")),
            "manual_source_pdf_page": 11,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _paperqa_settings(model: str, base_url: str) -> Any:
    from paperqa import Settings

    router = {
        "model_list": [
            {
                "model_name": "local-paperqa-r0",
                "litellm_params": {
                    "model": f"ollama/{model}",
                    "api_base": base_url,
                    "timeout": 300,
                    "num_ctx": 16384,
                    "max_tokens": 2000,
                    "think": False,
                },
            }
        ]
    }
    settings = Settings(
        llm="local-paperqa-r0",
        llm_config=router,
        summary_llm="local-paperqa-r0",
        summary_llm_config=router,
        embedding="ollama/nomic-embed-text",
        embedding_config={"api_base": base_url, "timeout": 300},
    )
    settings.parsing.use_doc_details = False
    settings.parsing.reader_config = {"chunk_chars": 1600, "overlap": 120}
    settings.parsing.multimodal = type(settings.parsing.multimodal).OFF
    settings.answer.evidence_skip_summary = True
    settings.answer.evidence_k = 10
    settings.answer.answer_max_sources = 5
    return settings


async def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    from paperqa import Docs

    installed = importlib.metadata.version("paper-qa")
    if installed != PAPERQA_VERSION:
        raise RuntimeError(f"Expected paper-qa=={PAPERQA_VERSION}, found {installed}")
    pdf_path = validate_pdf(args.pdf)
    data_root = args.data_dir.resolve()
    index_path = ensure_within(data_root / "index" / "paperqa-docs.pkl", data_root, "Index")
    output_path = ensure_within(args.output, data_root, "Output")
    pdf_hash = sha256_file(pdf_path)
    metadata = {"paperqa_version": installed, "pdf_sha256": pdf_hash}
    settings = _paperqa_settings(args.model, args.ollama_base_url)

    started = time.perf_counter()
    reused = index_path.exists()
    if reused:
        docs = load_trusted_index(index_path, data_root / "index", metadata)
    else:
        docs = Docs()
        await docs.aadd(
            pdf_path,
            citation=PAPER_CITATION,
            title=PAPER_TITLE,
            docname="CARRS-2023",
            settings=settings,
        )
        save_trusted_index(index_path, data_root / "index", docs, metadata)
    index_seconds = round(time.perf_counter() - started, 3)

    query_started = time.perf_counter()
    session = await docs.aquery(args.question, settings=settings)
    query_seconds = round(time.perf_counter() - query_started, 3)
    result = sanitize_session(
        session,
        run_metadata={
            "paperqa_version": installed,
            "python_version": sys.version.split()[0],
            "llm_model": args.model,
            "embedding_model": "nomic-embed-text",
            "ollama_base_url": args.ollama_base_url,
            "source_pdf": pdf_path.name,
            "source_pdf_sha256": pdf_hash,
            "source_url": PUBLIC_SOURCE_URL,
            "paper_title": PAPER_TITLE,
        },
        index_metadata={
            "reused": reused,
            "index_seconds": index_seconds,
            "query_seconds": query_seconds,
            "document_count": len(docs.docs),
            "text_chunk_count": len(docs.texts),
        },
    )
    write_json(output_path, result)
    return result


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    data_dir = repository / "data" / "paperqa2_r0"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=data_dir / "plos-medicine-carrs-followup.pdf")
    parser.add_argument("--data-dir", type=Path, default=data_dir)
    parser.add_argument("--output", type=Path, default=data_dir / "result.json")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen3:4b"))
    parser.add_argument(
        "--ollama-base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.ollama_base_url.rstrip("/") not in {"http://localhost:11434", "http://127.0.0.1:11434"}:
        raise ExperimentInputError("WP05 only permits a loopback Ollama endpoint")
    result = asyncio.run(run_experiment(args))
    print(
        json.dumps(
            {
                "output": str(args.output),
                "capabilities": result["capabilities"],
                "index": result["index"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
