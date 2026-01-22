"""
Main evaluation script for comparing RAG with and without a reranker.
"""

import asyncio
import asyncpg
import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# pylint: disable=wrong-import-position
from evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    map_at_k,
)
from rag.retriever import search_candidates
from rag.reranker import RerankerService

# pylint: enable=wrong-import-position

load_dotenv()


async def init_db_pool():
    """Initializes the database connection pool."""
    db_user = os.getenv("DB_USER", "admin")
    db_password = os.getenv("DB_PASSWORD", "admin")
    db_name = os.getenv("DB_NAME", "candidates")
    db_port = os.getenv("DB_PORT", "5433")

    return await asyncpg.create_pool(
        user=db_user,
        password=db_password,
        database=db_name,
        host="localhost",
        port=db_port,
        min_size=1,
        max_size=5,
    )


async def run_search_without_reranker(
    query: str, filters: Dict[str, Any], db_pool: asyncpg.Pool, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Search WITHOUT reranker (vector search only)."""
    candidates = await search_candidates(
        query=query, filters=filters, db_pool=db_pool, top_k=top_k
    )
    return candidates[:top_k]


async def run_search_with_reranker(
    query: str,
    filters: Dict[str, Any],
    db_pool: asyncpg.Pool,
    reranker: RerankerService,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Search WITH reranker (vector search + reranking)."""
    # Fetch more candidates for reranking
    candidates = await search_candidates(
        query=query, filters=filters, db_pool=db_pool, top_k=top_k
    )

    if not candidates or not query:
        return candidates[:top_k]

    # Rerank
    reranked = reranker.rank_candidates(query=query, candidates=candidates, top_k=top_k)

    return reranked


def calculate_aggregate_metrics(
    results: List[Dict[str, Any]], k_values: List[int]
) -> Dict[str, float]:
    """Calculates averaged metrics for a list of results."""
    metrics = {}
    for k in k_values:
        precision_scores = [
            precision_at_k(r["retrieved"], r["relevant"], k) for r in results
        ]
        recall_scores = [recall_at_k(r["retrieved"], r["relevant"], k) for r in results]
        ndcg_scores = [ndcg_at_k(r["retrieved"], r["relevant"], k) for r in results]

        if not precision_scores:
            metrics[f"precision@{k}"] = 0.0
            metrics[f"recall@{k}"] = 0.0
            metrics[f"ndcg@{k}"] = 0.0
        else:
            metrics[f"precision@{k}"] = sum(precision_scores) / len(precision_scores)
            metrics[f"recall@{k}"] = sum(recall_scores) / len(recall_scores)
            metrics[f"ndcg@{k}"] = sum(ndcg_scores) / len(ndcg_scores)

    metrics["mrr"] = mean_reciprocal_rank(results)
    metrics["map@5"] = map_at_k(results, k=5)

    return metrics


# pylint: disable=too-many-statements
async def evaluate_rag_system(test_queries_file: str = "evaluation/test_queries.json"):
    """
    Runs full evaluation of the RAG system.
    Compares results with and without a reranker.
    """

    # Load test queries
    print(f"📖 Loading test queries from {test_queries_file}...")
    with open(test_queries_file, "r", encoding="utf-8") as f:
        test_queries = json.load(f)

    print(f"✅ Loaded {len(test_queries)} test queries\n")

    # Initialization
    print("🔌 Connecting to database...")
    db_pool = await init_db_pool()

    print("🤖 Loading Reranker model...")
    reranker = RerankerService()

    print("\n" + "=" * 80)
    print("🚀 STARTING EVALUATION")
    print("=" * 80 + "\n")

    results_without_reranker = []
    results_with_reranker = []

    k_values = [1, 3, 5]

    # Run evaluation for each query
    for idx, test_query in enumerate(test_queries, start=1):
        query = test_query["query"]
        relevant_ids = test_query["relevant_candidates"]
        filters = test_query.get("filters", {})
        description = test_query.get("description", "")

        print(f"[{idx}/{len(test_queries)}] {description}")
        print(f"  Query: '{query}'")
        print(f"  Relevant candidates: {len(relevant_ids)}")

        # WITHOUT Reranker
        candidates_no_rerank = await run_search_without_reranker(
            query=query, filters=filters, db_pool=db_pool, top_k=5
        )
        retrieved_ids_no_rerank = [c["id"] for c in candidates_no_rerank]

        # WITH Reranker
        candidates_with_rerank = await run_search_with_reranker(
            query=query, filters=filters, db_pool=db_pool, reranker=reranker, top_k=5
        )
        retrieved_ids_with_rerank = [c["id"] for c in candidates_with_rerank]

        # Store results
        results_without_reranker.append(
            {
                "query": query,
                "retrieved": retrieved_ids_no_rerank,
                "relevant": relevant_ids,
            }
        )

        results_with_reranker.append(
            {
                "query": query,
                "retrieved": retrieved_ids_with_rerank,
                "relevant": relevant_ids,
            }
        )

        print("  ✓ Completed\n")

    # Calculate metrics using helper function
    print("\n" + "=" * 80)
    print("📊 EVALUATION RESULTS")
    print("=" * 80 + "\n")

    metrics_no_rerank = calculate_aggregate_metrics(results_without_reranker, k_values)
    metrics_with_rerank = calculate_aggregate_metrics(results_with_reranker, k_values)

    # Print Metrics
    print("🔵 WITHOUT RERANKER:")
    print("-" * 40)
    for metric, value in metrics_no_rerank.items():
        print(f"  {metric:15s}: {value:.4f}")
    print("\n")

    print("🟢 WITH RERANKER:")
    print("-" * 40)
    for metric, value in metrics_with_rerank.items():
        print(f"  {metric:15s}: {value:.4f}")
    print("\n")

    # Comparison (Improvement in %)
    print("📈 IMPROVEMENT WITH RERANKER:")
    print("-" * 40)

    improvements = {}
    for metric, no_rerank_val in metrics_no_rerank.items():
        with_rerank_val = metrics_with_rerank[metric]

        if no_rerank_val > 0:
            improvement_pct = ((with_rerank_val - no_rerank_val) / no_rerank_val) * 100
        else:
            improvement_pct = 0.0

        improvements[metric] = improvement_pct

        symbol = "🔺" if improvement_pct > 0 else "🔻" if improvement_pct < 0 else "➖"
        print(f"  {metric:15s}: {symbol} {improvement_pct:+.2f}%")

    print("\n" + "=" * 80)

    # Save results
    output_dir = "evaluation/results"
    os.makedirs(output_dir, exist_ok=True)

    report = {
        "test_queries_count": len(test_queries),
        "metrics_without_reranker": metrics_no_rerank,
        "metrics_with_reranker": metrics_with_rerank,
        "improvements_percent": improvements,
        "detailed_results": {
            "without_reranker": results_without_reranker,
            "with_reranker": results_with_reranker,
        },
    }

    output_file = f"{output_dir}/evaluation_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {output_file}")

    await db_pool.close()

    return report


if __name__ == "__main__":
    asyncio.run(evaluate_rag_system())
