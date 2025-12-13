from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import logging

from app.services.onboarding import (
    CandidateOnboardingService,
    CandidateInput,
    init_db_pool,
)
from app.services.pipeline import process_candidate_background
from rag.retriever import search_candidates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    print("Connecting to Database...")
    db_pool = await init_db_pool()
    yield
    print("Closing Database connection...")
    await db_pool.close()


app = FastAPI(lifespan=lifespan)


class SearchRequest(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    min_experience: Optional[int] = None
    top_k: int = 5


@app.post("/onboarding")
async def onboard_candidate(data: CandidateInput, background_tasks: BackgroundTasks):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    service = CandidateOnboardingService(db_pool)
    result = await service.create_candidate(data)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))

    candidate_id = result["candidate_id"]

    background_tasks.add_task(process_candidate_background, candidate_id, data, db_pool)

    return {"status": "processing", "candidate_id": candidate_id}


@app.post("/search")
async def search_endpoint(req: SearchRequest):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    filters = {"location": req.location, "min_experience": req.min_experience}

    results = await search_candidates(
        query=req.query, filters=filters, db_pool=db_pool, top_k=req.top_k
    )

    return {"results": results}
