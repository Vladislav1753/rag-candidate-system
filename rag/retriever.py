import logging
import asyncpg
from typing import Optional, Dict, Any
from rag.embedding.embedder import Embedder
import json

logger = logging.getLogger("retriever")
embedder = Embedder()


def _parse_json_field(field_data: Any, default_val: Any) -> Any:
    """
    Safe JSON parser helper.
    Internal utility for this module.
    """
    if field_data is None:
        return default_val
    if isinstance(field_data, str):
        try:
            return json.loads(field_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON field: {field_data[:50]}...")
            return default_val
    return field_data


async def search_candidates(
    query: Optional[str], filters: Dict[str, Any], db_pool: asyncpg.Pool, top_k: int = 5
) -> list[Dict[str, Any]]:
    """
    Performs a hybrid search in PostgreSQL:
    - If `query` is provided -> Semantic Search (Vector).
    - If `filters` are provided -> Exact match/Range filters (SQL).
    - If both are provided -> Hybrid Search (Filter first, then rank by similarity).
    """

    where_clauses = []
    args = []

    if filters.get("location"):
        args.append(filters["location"])
        # Dynamic parameter index: $1, $2, etc.
        where_clauses.append(f"location = ${len(args)}")

    if filters.get("min_experience"):
        args.append(filters["min_experience"])
        where_clauses.append(f"years_experience >= ${len(args)}")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    similarity_col = "0 as similarity"
    order_by_sql = "ORDER BY created_at DESC"

    if query:
        try:
            query_vector = embedder.embed_batch([query])[0]
            vector_str = str(query_vector)

            args.append(vector_str)
            vec_param_idx = len(args)

            similarity_col = (
                f"1 - (embedding <=> ${vec_param_idx}::vector) as similarity"
            )
            order_by_sql = f"ORDER BY embedding <=> ${vec_param_idx}::vector"

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    sql = f"""
            SELECT
                id,
                full_name,
                email,
                phone,
                location,
                spoken_languages,
                professional_title,
                years_experience,
                skills,
                tools_technologies,
                projects,
                work_history,
                education,
                certifications,
                summary_generated,
                {similarity_col}
            FROM candidates
            {where_sql}
            {order_by_sql}
            LIMIT ${len(args) + 1}
        """

    initial_fetch_k = top_k * 4 if query else top_k
    args.append(initial_fetch_k)

    results = []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)

            for row in rows:
                results.append(
                    {
                        "id": str(row["id"]),
                        "full_name": row["full_name"],
                        "email": row["email"],
                        "phone": row["phone"],
                        "location": row["location"],
                        "languages": row["spoken_languages"],
                        "professional_title": row["professional_title"],
                        "years_experience": row["years_experience"],
                        "skills": _parse_json_field(row["skills"], {}),
                        "tools": _parse_json_field(row["tools_technologies"], []),
                        "projects": _parse_json_field(row["projects"], []),
                        "work_history": _parse_json_field(row["work_history"], []),
                        "education": row["education"],
                        "certifications": row["certifications"],
                        "summary": row["summary_generated"],
                        "score": float(row["similarity"]),
                    }
                )

    except Exception as e:
        logger.error(f"Database search failed: {e}")
        return []

    return results
