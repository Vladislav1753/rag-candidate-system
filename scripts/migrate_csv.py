import asyncio
import os
import sys
import json
import uuid
from datetime import datetime
import pandas as pd
from app.services.onboarding import init_db_pool
from rag.embedding.embedder import Embedder

sys.path.append(os.getcwd())


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

            raw_skills = row.get("skills", "{}")

            if isinstance(raw_skills, str) and raw_skills.strip():
                skills_list = [s.strip() for s in raw_skills.split(",") if s.strip()]
                skills_json = json.dumps({"imported": skills_list})
            else:
                skills_json = json.dumps({})

            query = """
                    INSERT INTO candidates (id, full_name, professional_title, \
                                            years_experience, skills, location, \
                                            summary_generated, embedding, created_at, updated_at) \
                    VALUES ($1, $2, $3, $4, $5::json, $6, $7, $8::vector, $9, $9) \
                    """

            await conn.execute(
                query,
                cid,
                row.get("full_name", "Unknown"),
                row.get("professional_title", ""),
                int(row.get("years_experience", 0))
                if row.get("years_experience")
                else 0,
                skills_json,
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
