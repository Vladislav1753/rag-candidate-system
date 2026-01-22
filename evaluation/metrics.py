"""
Evaluation metrics for the RAG system.
Implements core metrics for assessing search quality.
"""

from typing import List, Dict, Any
import math


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    Precision@K: The proportion of relevant documents among the top-K results.

    Args:
        retrieved: list of returned candidate IDs (in ranked order)
        relevant: list of relevant candidate IDs
        k: number of top results to evaluate

    Returns:
        float: value between 0.0 and 1.0
    """
    if not retrieved or not relevant:
        return 0.0

    retrieved_at_k = retrieved[:k]
    relevant_set = set(relevant)

    hits = sum(1 for item in retrieved_at_k if item in relevant_set)

    return hits / k if k > 0 else 0.0


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    Recall@K: The proportion of relevant documents found out of all relevant documents.

    Args:
        retrieved: list of returned candidate IDs
        relevant: list of relevant candidate IDs
        k: number of top results to evaluate

    Returns:
        float: value between 0.0 and 1.0
    """
    if not relevant:
        return 0.0

    retrieved_at_k = retrieved[:k]
    relevant_set = set(relevant)

    hits = sum(1 for item in retrieved_at_k if item in relevant_set)

    return hits / len(relevant_set)


def mean_reciprocal_rank(results: List[Dict[str, Any]]) -> float:
    """
    MRR (Mean Reciprocal Rank): The average inverse rank of the first relevant document.

    Args:
        results: list of dictionaries with keys 'retrieved' and 'relevant'

    Returns:
        float: value between 0.0 and 1.0
    """
    if not results:
        return 0.0

    reciprocal_ranks = []

    for result in results:
        retrieved = result.get("retrieved", [])
        relevant = set(result.get("relevant", []))

        for rank, item_id in enumerate(retrieved, start=1):
            if item_id in relevant:
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            reciprocal_ranks.append(0.0)

    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0


def ndcg_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    NDCG@K (Normalized Discounted Cumulative Gain): Ranking quality metric.

    Args:
        retrieved: list of returned candidate IDs (in ranked order)
        relevant: list of relevant candidate IDs
        k: number of top results to evaluate

    Returns:
        float: value between 0.0 and 1.0
    """
    if not retrieved or not relevant:
        return 0.0

    retrieved_at_k = retrieved[:k]
    relevant_set = set(relevant)

    # DCG: Discounted Cumulative Gain
    dcg = 0.0
    for i, item_id in enumerate(retrieved_at_k, start=1):
        if item_id in relevant_set:
            # relevance = 1 for relevant, 0 for non-relevant
            dcg += 1.0 / math.log2(i + 1)

    # IDCG: Ideal DCG (if all relevant items were in top positions)
    idcg = 0.0
    for i in range(1, min(len(relevant), k) + 1):
        idcg += 1.0 / math.log2(i + 1)

    return dcg / idcg if idcg > 0 else 0.0


def map_at_k(results: List[Dict[str, Any]], k: int) -> float:
    """
    MAP@K (Mean Average Precision): The mean average precision across all queries.

    Args:
        results: list of dictionaries with keys 'retrieved' and 'relevant'
        k: number of top results to evaluate

    Returns:
        float: value between 0.0 and 1.0
    """
    if not results:
        return 0.0

    average_precisions = []

    for result in results:
        retrieved = result.get("retrieved", [])[:k]
        relevant = set(result.get("relevant", []))

        if not relevant:
            continue

        precisions = []
        num_hits = 0

        for i, item_id in enumerate(retrieved, start=1):
            if item_id in relevant:
                num_hits += 1
                precision_at_i = num_hits / i
                precisions.append(precision_at_i)

        if precisions:
            average_precisions.append(sum(precisions) / len(relevant))
        else:
            average_precisions.append(0.0)

    return (
        sum(average_precisions) / len(average_precisions) if average_precisions else 0.0
    )


def calculate_all_metrics(
    retrieved: List[str], relevant: List[str], k: int = 5
) -> Dict[str, float]:
    """
    Calculates all metrics for a single query.

    Args:
        retrieved: list of returned candidate IDs
        relevant: list of relevant candidate IDs
        k: number of top results

    Returns:
        dict: dictionary with metrics
    """
    return {
        f"precision@{k}": precision_at_k(retrieved, relevant, k),
        f"recall@{k}": recall_at_k(retrieved, relevant, k),
        f"ndcg@{k}": ndcg_at_k(retrieved, relevant, k),
    }
