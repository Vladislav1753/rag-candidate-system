import asyncio
import os
import json
import uuid
from datetime import datetime
import pandas as pd
from app.services.onboarding import init_db_pool
from rag.embedding.embedder import Embedder

CSV_PATH = "data/candidates_pool.csv"


async def migrate():
    print("🚀 Starting migration from CSV to PostgreSQL...")

    if not os.path.exists(CSV_PATH):
        print(f"File {CSV_PATH} not found!")
        return

    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    embedder = Embedder()
    pool = await init_db_pool()

    async with pool.acquire() as conn:
        for _, row in df.iterrows():
            cid = str(uuid.uuid4())
            now = datetime.utcnow()

            parts = [
                row.get("professional_title", ""),
                row.get("skills", ""),
                row.get("tools_technologies", ""),
                row.get("years_experience", ""),
                row.get("summary_generated", ""),
                row.get("location", ""),
            ]
            text_to_embed = " | ".join([str(p) for p in parts if p])

            print(f"Embedding: {row.get('full_name')}...")

            try:
                vector = embedder.embed_batch([text_to_embed])[0]
                vector_str = str(vector)
            except Exception as e:
                print(f"Skipping {row.get('full_name')} due to error: {e}")
                continue

            raw_skills = row.get("skills", "")
            if isinstance(raw_skills, str) and raw_skills.strip():
                skills_list = [s.strip() for s in raw_skills.split(",") if s.strip()]
            else:
                skills_list = []

            raw_tools = row.get("tools_technologies", "")
            if isinstance(raw_tools, str) and raw_tools.strip():
                tools_list = [t.strip() for t in raw_tools.split(",") if t.strip()]
            else:
                tools_list = []

            raw_langs = row.get("spoken_languages", "")
            if isinstance(raw_langs, str) and raw_langs.strip():
                langs_list = [l.strip() for l in raw_langs.split(",") if l.strip()]
            else:
                langs_list = []

            query = """
                    INSERT INTO candidates (
                        id, full_name, email, professional_title,
                        years_experience, skills, tools_technologies,
                        spoken_languages, location, summary_generated,
                        embedding, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::json, $7::json, $8, $9, $10, $11::vector, $12, $12)
                    """

            await conn.execute(
                query,
                cid,
                row.get("full_name", "Unknown"),
                row.get("email", ""),
                row.get("professional_title", ""),
                int(row.get("years_experience") or 0),
                json.dumps(skills_list),
                json.dumps(tools_list),
                langs_list,
                row.get("location", ""),
                row.get("summary_generated", ""),
                vector_str,
                now,
            )

    print("✅ Migration finished!")
    await pool.close()


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())
