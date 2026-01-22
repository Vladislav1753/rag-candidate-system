"""
Generation of synthetic test queries for RAG system evaluation.
Creates queries based on real candidates from the database.
"""

import asyncio
import asyncpg
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()


# pylint: disable=too-many-branches,too-many-statements
async def generate_test_queries() -> List[Dict[str, Any]]:
    """
    Generates test queries based on real candidates.

    Returns a list of dictionaries with:
    - query: search query
    - relevant_candidates: list of relevant candidate IDs
    - description: query description
    """

    db_user = os.getenv("DB_USER", "admin")
    db_password = os.getenv("DB_PASSWORD", "admin")
    db_name = os.getenv("DB_NAME", "candidates")
    db_port = os.getenv("DB_PORT", "5433")

    db_pool = await asyncpg.create_pool(
        user=db_user,
        password=db_password,
        database=db_name,
        host="localhost",
        port=db_port,
        min_size=1,
        max_size=5,
    )

    test_queries = []

    try:
        async with db_pool.acquire() as conn:
            # Fetch candidates for query generation
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    full_name,
                    professional_title,
                    years_experience,
                    location,
                    skills,
                    tools_technologies,
                    work_history,
                    projects,
                    summary_generated
                FROM candidates
                ORDER BY created_at DESC
                LIMIT 50
            """
            )

            # Strategy 1: Queries by professional title and experience
            for row in rows[:10]:
                title = row["professional_title"] or "Developer"
                exp = row["years_experience"] or 0

                test_queries.append(
                    {
                        "query": f"{title} with {exp}+ years experience",
                        "relevant_candidates": [str(row["id"])],
                        "description": f"Search by title and experience: {title}",
                    }
                )

            # Strategy 2: Queries by skills
            skills_map = {}
            for row in rows:
                skills_data = row["skills"]
                if isinstance(skills_data, str):
                    try:
                        skills_data = json.loads(skills_data)
                    except Exception:
                        continue

                if isinstance(skills_data, dict) and "manual_list" in skills_data:
                    skills = skills_data["manual_list"]
                elif isinstance(skills_data, list):
                    skills = skills_data
                else:
                    continue

                for skill in skills[:3]:  # Take the first 3 skills
                    if skill not in skills_map:
                        skills_map[skill] = []
                    skills_map[skill].append(str(row["id"]))

            # Create queries for popular skills
            for skill, candidate_ids in list(skills_map.items())[:10]:
                if len(candidate_ids) >= 1:
                    test_queries.append(
                        {
                            "query": f"Looking for someone with {skill} experience",
                            "relevant_candidates": candidate_ids[
                                :5
                            ],  # Top 5 candidates
                            "description": f"Skill-based search: {skill}",
                        }
                    )

            # Strategy 3: Queries by location and title
            location_map = {}
            for row in rows:
                loc = row["location"]
                title = row["professional_title"]
                if loc and title:
                    key = (loc, title)
                    if key not in location_map:
                        location_map[key] = []
                    location_map[key].append(str(row["id"]))

            for (loc, title), candidate_ids in list(location_map.items())[:5]:
                test_queries.append(
                    {
                        "query": f"{title} in {loc}",
                        "relevant_candidates": candidate_ids,
                        "description": f"Location + Title search: {title} in {loc}",
                        "filters": {"location": loc},
                    }
                )

            # Strategy 4: Complex queries
            for row in rows[:5]:
                skills_data = row["skills"]
                if isinstance(skills_data, str):
                    try:
                        skills_data = json.loads(skills_data)
                    except Exception:
                        continue

                if isinstance(skills_data, dict) and "manual_list" in skills_data:
                    skills = skills_data["manual_list"][:3]
                elif isinstance(skills_data, list):
                    skills = skills_data[:3]
                else:
                    continue

                title = row["professional_title"] or "Developer"
                skills_str = ", ".join(skills) if skills else ""

                if skills_str:
                    test_queries.append(
                        {
                            "query": f"Senior {title} skilled in {skills_str}",
                            "relevant_candidates": [str(row["id"])],
                            "description": "Complex query: title + skills",
                        }
                    )

    finally:
        await db_pool.close()

    return test_queries


async def save_test_queries(output_file: str = "evaluation/test_queries.json"):
    """Saves test queries to a JSON file."""
    queries = await generate_test_queries()

    os.makedirs("evaluation", exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(queries)} test queries")
    print(f"📁 Saved to: {output_file}")

    # Statistics
    with_filters = sum(1 for q in queries if "filters" in q)
    print("\n📊 Statistics:")
    print(f"  - Total queries: {len(queries)}")
    print(f"  - With filters: {with_filters}")
    print(f"  - Text only: {len(queries) - with_filters}")


if __name__ == "__main__":
    asyncio.run(save_test_queries())
