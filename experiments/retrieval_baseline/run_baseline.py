"""在已有笔记样例上保存 vector、BM25 与 hybrid 的可复现检索对比。"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from pathlib import Path

from app.rag.bm25_store import BM25Store
from app.rag.embeddings import DummyEmbeddingClient
from app.rag.faiss_store import FaissIndexStore
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.schemas import Chunk, RetrievalResult
from app.rag.splitter import split_markdown_document
from app.rag.vector_retriever import VectorRetriever

DEFAULT_NOTES_DIR = Path("experiments/minirag/notes")
DEFAULT_QUESTIONS_PATH = Path("experiments/retrieval_baseline/questions.json")
DEFAULT_TOP_K = 3
DEFAULT_DIMENSION = 16


def build_parser() -> argparse.ArgumentParser:
    """创建实验的显式输入参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes-dir", type=Path, default=DEFAULT_NOTES_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser


def read_questions(path: Path) -> list[dict[str, object]]:
    """读取人工标注的问题集；标注只引用本地 chunk_id。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("questions file must contain a JSON array")
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("query"), str):
            raise ValueError("every question must contain a string query")
        relevant_ids = item.get("relevant_chunk_ids")
        if not isinstance(relevant_ids, list) or not all(isinstance(value, str) for value in relevant_ids):
            raise ValueError("every question must contain string relevant_chunk_ids")
    return payload


def load_chunks(notes_dir: Path) -> list[Chunk]:
    """复用 WP09 Markdown splitter，保持评测数据源与生产索引一致。"""
    chunks: list[Chunk] = []
    for note_path in sorted(notes_dir.glob("*.md")):
        chunks.extend(
            split_markdown_document(
                note_path.read_text(encoding="utf-8-sig"),
                document_id=note_path.stem,
                source_path=str(note_path),
            )
        )
    if not chunks:
        raise ValueError("notes directory produced no chunks")
    return chunks


def calculate_metrics(results: list[RetrievalResult], relevant_ids: set[str]) -> dict[str, float]:
    """计算 Recall@K 与 MRR；以人工 chunk 标注代替主观判断。"""
    returned_ids = [result.chunk_id for result in results]
    relevant_returned = sum(chunk_id in relevant_ids for chunk_id in returned_ids)
    recall = relevant_returned / len(relevant_ids) if relevant_ids else 0.0
    first_rank = next(
        (index + 1 for index, chunk_id in enumerate(returned_ids) if chunk_id in relevant_ids),
        None,
    )
    return {"recall_at_k": recall, "mrr": 1 / first_rank if first_rank else 0.0}


async def run_experiment(args: argparse.Namespace) -> dict[str, object]:
    """构建一次真实索引并输出三种策略的逐题结果与聚合指标。"""
    if args.top_k <= 0:
        raise ValueError("top-k must be positive")
    chunks = load_chunks(args.notes_dir)
    questions = read_questions(args.questions)
    embedding = DummyEmbeddingClient(dimension=DEFAULT_DIMENSION)
    vectors = await embedding.embed([chunk.text for chunk in chunks])
    vector_store = FaissIndexStore(
        args.output.parent / "temporary_vector_index",
        dimension=embedding.dimension,
        embedding_model=embedding.model_name,
    )
    vector_store.build(chunks, vectors)
    bm25_store = BM25Store()
    bm25_store.build(chunks)
    query_vectors = await embedding.embed([str(question["query"]) for question in questions])
    vectors_by_query = {
        str(question["query"]): vector for question, vector in zip(questions, query_vectors)
    }
    vector_retriever = VectorRetriever(
        index_store=vector_store,
        embed_query=_make_query_vector_provider(vectors_by_query),
    )
    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_store,
        log_path=args.output.with_suffix(".retrieval.jsonl"),
    )
    strategy_metrics: dict[str, list[dict[str, float]]] = {"vector": [], "bm25": [], "hybrid": []}
    records: list[dict[str, object]] = []
    for question in questions:
        query = str(question["query"])
        relevant_ids = set(question["relevant_chunk_ids"])
        strategy_results = {
            "vector": vector_retriever.search(query, args.top_k),
            "bm25": bm25_store.search(query, args.top_k),
            "hybrid": hybrid_retriever.search(query, args.top_k),
        }
        records.append(
            {
                "query": query,
                "relevant_chunk_ids": sorted(relevant_ids),
                "strategies": {
                    name: [result.model_dump(mode="json") for result in results]
                    for name, results in strategy_results.items()
                },
            }
        )
        for name, results in strategy_results.items():
            strategy_metrics[name].append(calculate_metrics(results, relevant_ids))
    return {
        "top_k": args.top_k,
        "question_count": len(questions),
        "metrics": {
            name: {
                "mean_recall_at_k": sum(item["recall_at_k"] for item in values) / len(values),
                "mean_mrr": sum(item["mrr"] for item in values) / len(values),
            }
            for name, values in strategy_metrics.items()
        },
        "records": records,
    }


def _make_query_vector_provider(vectors_by_query: dict[str, list[float]]) -> Callable[[str], list[float]]:
    """将预先异步生成的测试查询向量作为同步 FAISS 适配器依赖注入。"""
    def embed_query(query: str) -> list[float]:
        try:
            return vectors_by_query[query]
        except KeyError as error:
            raise ValueError("query was not prepared for this baseline run") from error

    return embed_query


def main(argv: list[str] | None = None) -> int:
    """运行实验并原子化写入 JSON 结果。"""
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(run_experiment(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"experiment failed: {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved comparison metrics to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
