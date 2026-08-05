"""Mini-RAG 基线手工验证脚本（R2-WP09）。

流程（对齐实验说明 README.md 的四个步骤）：
  1. 索引 experiments/minirag/notes/ 下的 Obsidian 笔记；
  2. 提出 3 个问题并检索（默认问题可换）；
  3. 打印每条命中的 source_path 与 heading，供人工打开来源文件核对；
  4. 保存索引到 data/notes_index/，然后在新进程内加载（--skip-index 可跳过重建）。

Embedding 提供方由 --provider 选择（ollama | dummy），默认 dummy（开发用哈希向量，
非语义向量，仅验证引用可溯源）。禁用云端 embedding：ollama 不可达时抛 EmbeddingError。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Sequence

from app.core.config import Settings
from app.rag.embeddings import create_embedding_client
from app.rag.exceptions import NotesRAGError
from app.rag.faiss_store import read_index_metadata
from app.rag.notes_pipeline import NotesRAG

# 本实验笔记目录（相对仓库根目录）
DEFAULT_NOTES_DIR = Path("experiments/minirag/notes")
# 索引输出目录（默认对齐 Settings.NOTES_INDEX_DIR = data/notes_index，已被 .gitignore 忽略）
DEFAULT_INDEX_DIR = Path("data/notes_index")

DEFAULT_QUESTIONS = [
    "T790M 突变与 EGFR 耐药有什么关系？",
    "奥希替尼的耐药机制有哪些？",
    "系统评价中如何衡量异质性？",
]
DEFAULT_TOP_K = 2


class ExperimentError(ValueError):
    """实验输入或运行错误（由 main 统一捕获并转退出码）。"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes-dir", type=Path, default=DEFAULT_NOTES_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument(
        "--provider",
        choices=("ollama", "dummy"),
        default=os.getenv("EMBEDDING_PROVIDER", "dummy"),
        help="embedding 提供方；默认读取 env EMBEDDING_PROVIDER，否则 dummy",
    )
    parser.add_argument(
        "--questions",
        default=";".join(DEFAULT_QUESTIONS),
        help="分号分隔的检索问题；缺省使用内置 3 个问题",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="跳过重建，只验证从磁盘加载已有索引",
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser


def build_rag(args: argparse.Namespace, settings: Settings) -> NotesRAG:
    """按 CLI 参数与配置组装 NotesRAG（embedding 只允许 ollama/dummy）。"""
    if args.provider == "ollama" and not settings.OLLAMA_EMBEDDING_MODEL.strip():
        raise ExperimentError(
            "OLLAMA_EMBEDDING_MODEL 未配置；请在 .env 设置本地 Ollama 模型名，或改用 --provider dummy"
        )
    embedding = create_embedding_client(
        provider=args.provider,
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBEDDING_MODEL or "nomic-embed-text",
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        # dummy 的维度仅由配置决定；Ollama 的维度在首次 embed 后确定
        dimension=settings.EMBEDDING_DIMENSION if args.provider == "dummy" else None,
    )
    return NotesRAG(index_dir=args.index_dir, embedding=embedding)


def _truncate(text: str, limit: int = 80) -> str:
    """控制台安全：折叠空白并截断，避免整块文本刷屏。"""
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _console_safe(value: str) -> str:
    """按当前控制台编码安全输出（避免 GBK 终端打印中文异常）。"""
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="backslashreplace").decode(encoding)


async def _run_queries(rag: NotesRAG, questions: Sequence[str], top_k: int) -> None:
    """对每个问题检索并打印命中结果，便于人工核对 source_path 与 heading。"""
    for question in questions:
        print(f"[Q] {_console_safe(question)}")
        results = await rag.search(question, top_k=top_k)
        if not results:
            print("  - 无命中")
            continue
        for result in results:
            print(f"  - {_console_safe(_truncate(result.text))}")
            print(f"    source: {_console_safe(result.source_path)}")
            print(f"    heading: {_console_safe(result.heading)}")
            print(f"    score: {result.score:.4f}")
        print()


async def _run(args: argparse.Namespace) -> None:
    settings = Settings()
    if not args.skip_index:
        if not args.notes_dir.is_dir():
            raise ExperimentError(f"笔记目录不存在: {args.notes_dir}")
        rag = build_rag(args, settings)
        stats = await rag.index(args.notes_dir)
        print(
            f"[索引] 文档数={stats.document_count}, 分块数={stats.chunk_count}, "
            f"维度={stats.dimension}, 索引目录={args.index_dir}"
        )
        rag.save_index()
        print(f"[保存] 索引已保存到 {args.index_dir}")
        await _run_queries(rag, args.questions, args.top_k)
    else:
        if not args.index_dir.is_dir():
            raise ExperimentError(f"索引目录不存在，请先建立索引: {args.index_dir}")
        embedding_model, stored_dimension = read_index_metadata(args.index_dir)
        print(
            f"[加载] 索引加载成功: {args.index_dir} "
            f"(dimension={stored_dimension}, model={embedding_model})"
        )
        rag = build_rag(args, settings)
        try:
            rag.load_index()
        except NotesRAGError as error:
            raise ExperimentError(f"加载索引失败（{error.code}）: {error.message}") from error
        _run_queries(rag, args.questions, args.top_k)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.questions = [item.strip() for item in args.questions.split(";") if item.strip()]
    if not args.questions:
        print("错误: --questions 为空", file=sys.stderr)
        return 2
    if args.top_k <= 0:
        print("错误: --top-k 必须为正整数", file=sys.stderr)
        return 2
    try:
        asyncio.run(_run(args))
        return 0
    except (NotesRAGError, ExperimentError) as error:
        message = getattr(error, "message", str(error))
        code = getattr(error, "code", "experiment")
        print(f"实验失败 [{code}]: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
