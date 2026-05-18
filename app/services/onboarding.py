import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import asyncpg
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field

load_dotenv()


class CandidateInput(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    spoken_languages: list[str] | None = None
    professional_title: str | None = None
    years_experience: int | None = None

    skills: dict[str, Any] | None = None
    tools_technologies: dict[str, Any] | None = None
    projects: dict[str, Any] | None = None
    work_history: dict[str, Any] | None = None

    education: str | None = None
    certifications: str | None = None


class CandidateOnboardingService:
    def __init__(self, db_pool: asyncpg.pool.Pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger("onboarding")

    async def create_candidate(self, data: CandidateInput) -> dict:
        """Adds a candidate to PostgreSQL."""

        candidate_id = str(uuid.uuid4())
        now = datetime.utcnow()

        skills_json = json.dumps(data.skills) if data.skills else None
        tools_json = (
            json.dumps(data.tools_technologies) if data.tools_technologies else None
        )
        projects_json = json.dumps(data.projects) if data.projects else None
        history_json = json.dumps(data.work_history) if data.work_history else None

        query = """
            INSERT INTO candidates (
               id, full_name, email, phone, location, spoken_languages,
               professional_title, years_experience, skills, tools_technologies,
               projects, education, certifications, work_history,
               summary_generated, created_at, updated_at
            ) VALUES (
               $1, $2, $3, $4, $5, $6, $7, $8,
               $9::json, $10::json, $11::json,
               $12, $13, $14::json,
               NULL, $15, $16
            )
        """

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    query,
                    candidate_id,
                    data.full_name,
                    data.email,
                    data.phone,
                    data.location,
                    data.spoken_languages,
                    data.professional_title,
                    data.years_experience,
                    skills_json,
                    tools_json,
                    projects_json,
                    data.education,
                    data.certifications,
                    history_json,
                    now,
                    now,
                )

            return {"status": "success", "candidate_id": candidate_id}

        except asyncpg.exceptions.PostgresError as err:
            self.logger.exception("Failed to insert candidate: %s", err)
            return {
                "status": "error",
                "error": "Database write failed (Possible duplicate or invalid data).",
            }


async def init_db_pool() -> asyncpg.pool.Pool:
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 5433))

    print(
        f"DEBUG CONNECTION: Host={db_host}, Port={db_port}, User={db_user}, Pass={db_pass}"
    )

    return await asyncpg.create_pool(
        user=db_user,
        password=db_pass,
        database=os.getenv("DB_NAME", "candidates"),
        host=db_host,
        port=db_port,
        min_size=1,
        max_size=5,
    )
