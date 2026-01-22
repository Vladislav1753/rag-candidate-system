"""
Evaluation package for RAG system.
Contains metrics, test query generation, and reporting tools.
"""

from .metrics import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    map_at_k,
    calculate_all_metrics,
)

__all__ = [
    "precision_at_k",
    "recall_at_k",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "map_at_k",
    "calculate_all_metrics",
]
