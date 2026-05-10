"""Evaluate retrieval (Recall@K, MRR) and generation (answer accuracy).

Loads Q&A pairs from `tests/fixtures/qa_pairs.json` by default. Each entry:
{
  "question": "...",
  "expected_answer_contains": ["12"],
  "expected_source": "01_so_tay_nhan_vien_2024.pdf",
  "expected_page": 12
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.generation.llm import OllamaLLM
from src.search.embedder import BGEEmbedder
from src.search.reranker import CrossEncoderReranker
from src.search.retriever import HybridRetriever
from src.utils.logger import get_logger, setup_logging


def evaluate_retrieval(retriever: HybridRetriever, qa: list[dict[str, Any]], k: int) -> dict[str, float]:
    hits = 0
    mrr_sum = 0.0
    for item in qa:
        results = retriever.search(item["question"], limit=k)
        sources = [r["metadata"].get("source", "") for r in results]
        expected = item["expected_source"]
        if expected in sources:
            hits += 1
            mrr_sum += 1.0 / (sources.index(expected) + 1)
    total = max(len(qa), 1)
    return {f"recall@{k}": hits / total, "mrr": mrr_sum / total}


def evaluate_generation(
    retriever: HybridRetriever,
    reranker: CrossEncoderReranker,
    llm: OllamaLLM,
    qa: list[dict[str, Any]],
    top_k: int,
) -> dict[str, float]:
    correct = 0
    for item in qa:
        retrieved = retriever.search(item["question"], limit=30)
        reranked = reranker.rerank(item["question"], retrieved, top_k=top_k)
        answer = llm.generate(item["question"], reranked) if reranked else ""
        if any(exp.lower() in answer.lower() for exp in item.get("expected_answer_contains", [])):
            correct += 1
    return {"answer_accuracy": correct / max(len(qa), 1)}


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--qa",
        type=str,
        default=str(Path("tests/fixtures/qa_pairs.json")),
        help="Path to QA pairs JSON file.",
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--skip-generation", action="store_true")
    args = parser.parse_args()

    qa_path = Path(args.qa)
    if not qa_path.exists():
        raise SystemExit(f"QA file not found: {qa_path}")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d Q&A pairs from %s", len(qa), qa_path)

    settings = get_settings()
    embedder = BGEEmbedder()
    retriever = HybridRetriever(embedder=embedder)

    ret_metrics = evaluate_retrieval(retriever, qa, k=args.k)
    logger.info("Retrieval: %s", ret_metrics)

    if not args.skip_generation:
        reranker = CrossEncoderReranker()
        llm = OllamaLLM()
        gen_metrics = evaluate_generation(
            retriever, reranker, llm, qa, top_k=settings.top_k_rerank
        )
        logger.info("Generation: %s", gen_metrics)


if __name__ == "__main__":
    main()
