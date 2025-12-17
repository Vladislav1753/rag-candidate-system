import logging
import asyncpg
from typing import Optional, Dict, Any
from rag.embedding.embedder import Embedder
import json

logger = logging.getLogger("retriever")
embedder = Embedder()


async def search_candidates(
    query: Optional[str], filters: Dict[str, Any], db_pool: asyncpg.Pool, top_k: int = 5
):
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
                skills,
                professional_title,
                summary_generated,
                years_experience,
                location,
                phone,
                education,
                spoken_languages,
                {similarity_col}
            FROM candidates
            {where_sql}
            {order_by_sql}
            LIMIT ${len(args) + 1}
        """

    args.append(top_k)

    results = []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)

            for row in rows:
                skills_data = row["skills"]
                if isinstance(skills_data, str):
                    try:
                        skills_data = json.loads(skills_data)
                    except json.JSONDecodeError:
                        skills_data = {}

                results.append(
                    {
                        "id": str(row["id"]),
                        "full_name": row["full_name"],
                        "email": row["email"],
                        "professional_title": row["professional_title"],
                        "location": row["location"],
                        "years_experience": row["years_experience"],
                        "summary": row["summary_generated"],
                        "skills": skills_data,
                        "phone": row["phone"],
                        "education": row["education"],
                        "languages": row["spoken_languages"],
                        "score": float(row["similarity"]),
                    }
                )

    except Exception as e:
        logger.error(f"Database search failed: {e}")
        return []

    return results
